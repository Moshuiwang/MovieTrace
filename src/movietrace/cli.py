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
    print("[3/5] Matching against baseline...", end=" ", flush=True)
    try:
        from movietrace.pipeline.baseline_matching import run_baseline_matching
        match_result = run_baseline_matching()
        print(f"OK (high={match_result.get('high',0)} medium={match_result.get('medium',0)} "
              f"low={match_result.get('low',0)} no_match={match_result.get('no_match',0)})")
    except Exception as exc:
        print(f"FAILED: {exc}")
        return 1

    # Step 4: Generate report
    print("[4/5] Generating daily report...", end=" ", flush=True)
    try:
        from movietrace.reports.daily_writer import write_daily_report
        report_path = write_daily_report(report_date)
        print(f"OK → {report_path}")
    except Exception as exc:
        print(f"FAILED: {exc}")
        return 1

    # Step 5: Baseline tracking (P1.5-D)
    cfg = _load_config()
    bt_cfg = cfg.get("baseline_tracking", {})
    if bt_cfg.get("enabled", True):
        print("[5/5] Baseline tracking (new season detection)...", end=" ", flush=True)
        try:
            from movietrace.pipeline.baseline_tracking import run_baseline_tracking

            tmdb_token = _load_tmdb_token()
            bt_result = run_baseline_tracking(
                db_path="data/movietrace.db",
                tmdb_token=tmdb_token,
                dry_run=dry_run,
            )
            print(
                f"OK (polled={bt_result.get('polled',0)} "
                f"detected={bt_result.get('detected',0)} "
                f"written={bt_result.get('written',0)})"
            )
        except Exception as exc:
            print(f"FAILED: {exc}")
            return 1
    else:
        print("[5/5] Baseline tracking skipped (disabled in config.yaml)")

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
    """Query local baseline data (A库 upstream_programs + canonical_items)."""
    conn = connect_database("data/movietrace.db")
    fmt = args.format or "table"

    if args.query:
        rows = _query_upstream(conn, args.query)
        _output_upstream_rows(rows, fmt)
    else:
        # A库 upstream_programs stats
        up_total = conn.execute("select count(*) from upstream_programs").fetchone()[0]
        up_online = conn.execute(
            "select count(*) from upstream_programs where online_flag = '1'"
        ).fetchone()[0]
        up_with_s = conn.execute(
            "select count(*) from upstream_programs where online_flag = '1' and name like '%S__%'"
        ).fetchone()[0]

        # Canonical items stats
        ci_total = conn.execute("select count(*) from canonical_items").fetchone()[0]
        ci_tv = conn.execute(
            "select count(*) from canonical_items where content_type = 'tv'"
        ).fetchone()[0]
        ci_movie = conn.execute(
            "select count(*) from canonical_items where content_type = 'movie'"
        ).fetchone()[0]

        # Virtual series stats
        vs_total = conn.execute("select count(*) from virtual_series").fetchone()[0]

        # Content updates stats
        cu_new_season = conn.execute(
            "select count(*) from content_updates where update_type = 'new_season'"
        ).fetchone()[0]

        # Legacy baseline_items stats
        bl_total = conn.execute("select count(*) from baseline_items").fetchone()[0]

        print("A库（upstream_programs）:")
        print(f"  总节目数: {up_total}")
        print(f"  上架中 (online_flag=1): {up_online}")
        print(f"  含季号 (S\d\d): {up_with_s}")
        print(f"  推测电影 (无季号): {up_online - up_with_s}")
        print()
        print("B库（canonical_items + virtual_series）:")
        print(f"  canonical_items: {ci_total} (TV: {ci_tv}, Movie: {ci_movie})")
        print(f"  virtual_series: {vs_total}")
        print(f"  content_updates (new_season): {cu_new_season}")
        print()
        print("Legacy（baseline_items）:")
        print(f"  baseline_items: {bl_total} (历史飞书导入，保留不动)")
        print()
        print("Phase 1.5 Status: 全部任务包已完成")
        print("  Next: Phase 1.6 (首次真实运行 + 验收)")

    conn.close()
    return 0


def _query_upstream(conn, query: str) -> list[tuple]:
    """Parse simple query string and execute against upstream_programs."""
    conditions = []
    params = []
    for part in query.split(" AND "):
        part = part.strip()
        if "=" in part:
            key, val = part.split("=", 1)
            key = key.strip()
            val = val.strip()
            valid_cols = {"name", "online_flag", "program_status", "code"}
            if key in valid_cols:
                conditions.append(f"{key} like ?")
                params.append(f"%{val}%")

    sql = "select id, name, online_flag, program_status from upstream_programs"
    if conditions:
        sql += " where " + " and ".join(conditions)
    sql += " limit 50"

    return conn.execute(sql, params).fetchall()


def _output_upstream_rows(rows: list[tuple], fmt: str) -> None:
    if not rows:
        print("No results.")
        return

    if fmt == "json":
        data = [
            {"id": r[0], "name": r[1], "online_flag": r[2], "program_status": r[3]}
            for r in rows
        ]
        print(json.dumps(data, indent=2, ensure_ascii=False, default=str))
    elif fmt == "table":
        print(f"| ID | Name | Online | Status |")
        print(f"|----|------|--------|--------|")
        for r in rows:
            print(f"| {r[0]} | {r[1] or 'N/A'} | {r[2] or 'N/A'} | {r[3] or 'N/A'} |")
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


def _load_config(path: str = "config.yaml") -> dict:
    try:
        import yaml

        with open(path) as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def _load_tmdb_token(
    secrets_path: str = "/tmp/movietrace_phase0_secrets.json",
) -> str:
    secrets = json.loads(open(secrets_path).read())
    token = (secrets.get("tmdb") or {}).get("api_read_access_token")
    if not token:
        raise RuntimeError("TMDb API token not found in secrets file")
    return token


# ── baseline-track ───────────────────────────────────────────────────────


def cmd_baseline_track(args: argparse.Namespace) -> int:
    """Run baseline tracking (new season detection)."""
    cfg = _load_config()
    bt_cfg = cfg.get("baseline_tracking", {})
    if not bt_cfg.get("enabled", True):
        print("baseline_tracking is disabled in config.yaml (enabled: false)")
        return 0

    print("MovieTrace baseline-track")
    print(f"Dry-run: {args.dry_run}")
    if args.limit:
        print(f"Limit: {args.limit}")
    print()

    try:
        from movietrace.pipeline.baseline_tracking import run_baseline_tracking

        tmdb_token = _load_tmdb_token()
        result = run_baseline_tracking(
            db_path=args.db or "data/movietrace.db",
            tmdb_token=tmdb_token,
            dry_run=args.dry_run,
            limit=args.limit,
        )

        print(f"Plan size: {result.get('plan_size', 0)}")
        print(f"Polled:    {result.get('polled', 0)}")
        print(f"Detected:  {result.get('detected', 0)}")
        print(f"Written:   {result.get('written', 0)}")
        print(f"Errors:    {result.get('errors', 0)}")
        print()
        print("✓ Baseline tracking complete")
        return 0
    except Exception as exc:
        print(f"✗ Baseline tracking failed: {exc}")
        return 1


# ── export-recommendations ────────────────────────────────────────────────


def cmd_export_recommendations(args: argparse.Namespace) -> int:
    """Export content_updates as MD + JSON report files."""
    print("MovieTrace export-recommendations")
    print(f"Days: {args.days}")
    print(f"Output dir: {args.output_dir}")
    print()

    try:
        from movietrace.reports.export_writer import export_recommendations

        result = export_recommendations(
            db_path=args.db or "data/movietrace.db",
            output_dir=args.output_dir,
            days=args.days,
            dry_run=args.dry_run,
        )

        if result.get("dry_run"):
            print(f"[DRY-RUN] Would export {result.get('total_items', 0)} items")
        else:
            print(f"MD:   {result.get('md_path', '')}")
            print(f"JSON: {result.get('json_path', '')}")
            print(f"Total items: {result.get('total_items', 0)}")

        print()
        print("✓ Export complete")
        return 0
    except Exception as exc:
        print(f"✗ Export failed: {exc}")
        return 1


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

    # baseline-track
    p_track = sub.add_parser("baseline-track", help="Run baseline new season detection")
    p_track.add_argument("--db", help="Database path")
    p_track.add_argument("--dry-run", action="store_true")
    p_track.add_argument("--limit", type=int)

    # export-recommendations
    p_export = sub.add_parser("export-recommendations", help="Export recommendations to MD+JSON")
    p_export.add_argument("--db", help="Database path")
    p_export.add_argument("--days", type=int, default=7, help="Days to cover (default: 7)")
    p_export.add_argument("--output-dir", default="reports", help="Output directory")
    p_export.add_argument("--dry-run", action="store_true")

    args = parser.parse_args()

    handlers = {
        "daily-discover": cmd_daily_discover,
        "validate-feishu": cmd_validate_feishu,
        "inspect-baseline": cmd_inspect_baseline,
        "check-feishu-schema": cmd_check_feishu_schema,
        "baseline-track": cmd_baseline_track,
        "export-recommendations": cmd_export_recommendations,
    }

    handler = handlers.get(args.command)
    if handler:
        sys.exit(handler(args))


if __name__ == "__main__":
    main()
