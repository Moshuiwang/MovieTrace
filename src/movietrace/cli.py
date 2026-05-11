"""MovieTrace CLI — Phase 1 V1 MVP daily operations.

Usage:
    PYTHONPATH=src python -m movietrace.cli daily-discover [--date YYYY-MM-DD] [--dry-run]
    PYTHONPATH=src python -m movietrace.cli validate-feishu
    PYTHONPATH=src python -m movietrace.cli inspect-baseline [--query Q] [--format json|table]
    PYTHONPATH=src python -m movietrace.cli check-feishu-schema
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime

from movietrace.db.schema import connect_database

# ── daily-discover ──────────────────────────────────────────────────────


def cmd_daily_discover(args: argparse.Namespace) -> int:
    """Run the full daily discovery pipeline."""
    report_date = _parse_date_arg(args.date) or date.today()
    date_str = report_date.isoformat()
    dry_run = args.dry_run

    print(f"MovieTrace daily-discover for {date_str}")
    print(f"Dry-run: {dry_run}")
    print()

    # Step 1: Fetch FlixPatrol data
    print("[1/4] Fetching FlixPatrol data...", end=" ", flush=True)
    try:
        from movietrace.pipeline.discovery import _ensure_fp_data
        conn = connect_database("data/movietrace.db")
        _ensure_fp_data(conn, date_str)
        conn.close()
        print("OK")
    except Exception as exc:
        print(f"FAILED: {exc}")
        return 1

    # Step 2: Discovery (score + merge + write candidates)
    print("[2/4] Scoring candidates...", end=" ", flush=True)
    try:
        from movietrace.pipeline.discovery import run_discovery
        result = run_discovery(date_from=date_str, dry_run=False)
        stats = result.get("stats", {})
        print(f"OK ({stats.get('total', 0)} candidates)")
    except Exception as exc:
        print(f"FAILED: {exc}")
        return 1

    # Step 3: Baseline matching
    print("[3/4] Matching against baseline...", end=" ", flush=True)
    try:
        from movietrace.pipeline.baseline_matching import run_baseline_matching
        match_result = run_baseline_matching()
        print(f"OK (high={match_result.get('high',0)} medium={match_result.get('medium',0)} "
              f"low={match_result.get('low',0)} no_match={match_result.get('no_match',0)})")
    except Exception as exc:
        print(f"FAILED: {exc}")
        return 1

    # Step 4: Generate report + write Feishu
    print("[4/4] Generating report and writing Feishu...", end=" ", flush=True)
    try:
        from movietrace.reports.daily_writer import write_daily_report
        report_path = write_daily_report(report_date)
        print(f"OK")

        from movietrace.feishu.recommendation_writer import write_recommendations
        feishu_stats = write_recommendations(dry_run=dry_run)
        print(f"     Feishu: insert={feishu_stats['insert']} "
              f"skip={feishu_stats['skip']} error={feishu_stats['error']}")
        print(f"     Report: {report_path}")
    except Exception as exc:
        print(f"FAILED: {exc}")
        return 1

    print()
    print("✓ Daily discovery complete")
    return 0


# ── validate-feishu ─────────────────────────────────────────────────────


def cmd_validate_feishu(args: argparse.Namespace) -> int:
    """Validate Feishu API connectivity and token."""
    secrets_path = "/tmp/movietrace_phase0_secrets.json"

    # Load secrets
    try:
        secrets = json.loads(open(secrets_path).read())
    except FileNotFoundError:
        print("✗ Secrets file not found:", secrets_path)
        return 1

    feishu = secrets.get("feishu", {})
    app_id = feishu.get("app_id")
    app_secret = feishu.get("app_secret")
    base_token = feishu.get("base_app_token")

    if not app_id or not app_secret:
        print("✗ feishu.app_id or app_secret not configured")
        return 1

    # Test token
    try:
        from movietrace.feishu.baseline import fetch_tenant_access_token
        token = fetch_tenant_access_token(app_id, app_secret)
        print("✓ Feishu API reachable")
        print(f"✓ Access token valid ({token[:8]}...)")
    except Exception as exc:
        print(f"✗ Token request failed: {exc}")
        return 1

    # Test table access
    if base_token:
        test_table_id = feishu.get("test_table_id") or feishu.get("baseline_table_id")
        if test_table_id:
            try:
                from movietrace.feishu.baseline import fetch_bitable_records
                records = fetch_bitable_records(
                    tenant_access_token=token,
                    app_token=base_token,
                    table_id=test_table_id,
                    page_size=1,
                )
                print(f"✓ Can access table: {test_table_id} ({len(records)} record(s) visible)")
            except Exception as exc:
                print(f"⚠ Table access failed: {exc}")
        else:
            print("⚠ No table_id configured for validation")

    return 0


# ── inspect-baseline ────────────────────────────────────────────────────


def cmd_inspect_baseline(args: argparse.Namespace) -> int:
    """Query local baseline data."""
    conn = connect_database("data/movietrace.db")
    fmt = args.format or "table"

    if args.query:
        rows = _query_baseline(conn, args.query)
        _output_rows(rows, fmt)
    else:
        # Summary stats
        total = conn.execute("select count(*) from baseline_items").fetchone()[0]
        movies = conn.execute(
            "select count(*) from baseline_items where content_type = 'movie'"
        ).fetchone()[0]
        tv = conn.execute(
            "select count(*) from baseline_items where content_type = 'tv_show'"
        ).fetchone()[0]
        matched = conn.execute(
            "select count(*) from baseline_items where match_status = 'matched'"
        ).fetchone()[0]
        canonical = conn.execute(
            "select count(distinct canonical_item_id) from baseline_items where canonical_item_id is not null"
        ).fetchone()[0]

        n_candidates = conn.execute("select count(*) from candidates").fetchone()[0]
        n_matches = conn.execute("select count(*) from candidate_matches").fetchone()[0]

        print("Baseline Summary:")
        print(f"  Total baseline items: {total}")
        print(f"  Movies: {movies}")
        print(f"  TV Shows: {tv}")
        print(f"  Matched to canonical: {matched}")
        print(f"  Unique canonical items: {canonical}")
        print()
        print("Phase 1 Status:")
        print(f"  Candidates (today): {n_candidates}")
        print(f"  Candidate matches: {n_matches}")

    conn.close()
    return 0


def _query_baseline(conn, query: str) -> list[tuple]:
    """Parse simple query string and execute against baseline_items."""
    conditions = []
    params = []
    for part in query.split(" AND "):
        part = part.strip()
        if "=" in part:
            key, val = part.split("=", 1)
            key = key.strip()
            val = val.strip()
            valid_cols = {"title", "year", "content_type", "match_status", "content_granularity"}
            if key in valid_cols:
                conditions.append(f"{key} like ?")
                params.append(f"%{val}%")

    sql = "select id, title, content_type, year, match_status from baseline_items"
    if conditions:
        sql += " where " + " and ".join(conditions)
    sql += " limit 50"

    return conn.execute(sql, params).fetchall()


def _output_rows(rows: list[tuple], fmt: str) -> None:
    if not rows:
        print("No results.")
        return

    if fmt == "json":
        data = [
            {"id": r[0], "title": r[1], "type": r[2], "year": r[3], "status": r[4]}
            for r in rows
        ]
        print(json.dumps(data, indent=2, ensure_ascii=False, default=str))
    elif fmt == "table":
        print(f"| ID | Title | Type | Year | Status |")
        print(f"|----|-------|------|------|--------|")
        for r in rows:
            print(f"| {r[0]} | {r[1] or 'N/A'} | {r[2] or 'N/A'} | {r[3] or 'N/A'} | {r[4] or 'N/A'} |")
        print(f"\n{len(rows)} row(s)")
    else:
        # CSV
        for r in rows:
            print(",".join(str(c or "") for c in r))


# ── check-feishu-schema ─────────────────────────────────────────────────


def cmd_check_feishu_schema(args: argparse.Namespace) -> int:
    """Verify Feishu recommendation table schema matches expected fields."""
    expected_fields = {
        "content_update_id", "title", "release_year", "content_type",
        "hot_score", "platforms", "discovery_source", "reason_text",
        "review_status", "batch_id", "fulfillment_status",
    }

    secrets_path = "/tmp/movietrace_phase0_secrets.json"
    try:
        secrets = json.loads(open(secrets_path).read())
    except FileNotFoundError:
        print("✗ Secrets file not found")
        return 1

    feishu = secrets.get("feishu", {})
    app_id = feishu.get("app_id")
    app_secret = feishu.get("app_secret")
    base_token = feishu.get("base_app_token")
    test_table_id = feishu.get("test_table_id")

    if not all([app_id, app_secret, base_token, test_table_id]):
        print("✗ Missing Feishu configuration in secrets")
        return 1

    try:
        from movietrace.feishu.baseline import fetch_tenant_access_token, fetch_bitable_records
        token = fetch_tenant_access_token(app_id, app_secret)
        records = fetch_bitable_records(
            tenant_access_token=token,
            app_token=base_token,
            table_id=test_table_id,
            page_size=1,
        )

        if records:
            actual_fields = set()
            for record in records:
                fields = record.get("fields", {})
                actual_fields.update(fields.keys())

            print("Expected fields:")
            for f in sorted(expected_fields):
                status = "✓" if f in actual_fields else "✗"
                print(f"  {status} {f}")

            missing = expected_fields - actual_fields
            extra = actual_fields - expected_fields

            if missing:
                print(f"\n⚠ Missing fields: {', '.join(sorted(missing))}")
            if extra:
                print(f"\nℹ Extra fields: {', '.join(sorted(extra))}")
            if not missing:
                print("\n✓ Schema matches expected fields")
        else:
            print("⚠ No records in test table — cannot verify schema")
    except Exception as exc:
        print(f"✗ Feishu API error: {exc}")
        return 1

    return 0


# ── Argument parsing ────────────────────────────────────────────────────


def _parse_date_arg(date_str: str | None) -> date | None:
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        print(f"Invalid date format: {date_str}. Use YYYY-MM-DD.", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="movietrace",
        description="MovieTrace Phase 1 CLI",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # daily-discover
    p_discover = sub.add_parser("daily-discover", help="Run full daily discovery pipeline")
    p_discover.add_argument("--date", help="Date in YYYY-MM-DD format")
    p_discover.add_argument("--dry-run", action="store_true", help="Skip Feishu write")

    # validate-feishu
    sub.add_parser("validate-feishu", help="Validate Feishu API connectivity")

    # inspect-baseline
    p_inspect = sub.add_parser("inspect-baseline", help="Query local baseline data")
    p_inspect.add_argument("--query", help="Filter: title=X AND year=YYYY")
    p_inspect.add_argument("--format", choices=["json", "table", "csv"], default="table")

    # check-feishu-schema
    sub.add_parser("check-feishu-schema", help="Verify Feishu table schema")

    args = parser.parse_args()

    handlers = {
        "daily-discover": cmd_daily_discover,
        "validate-feishu": cmd_validate_feishu,
        "inspect-baseline": cmd_inspect_baseline,
        "check-feishu-schema": cmd_check_feishu_schema,
    }

    handler = handlers.get(args.command)
    if handler:
        sys.exit(handler(args))


if __name__ == "__main__":
    main()
