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
    """Run the full multi-source daily discovery pipeline (P1.7-D)."""
    report_date = _parse_date_arg(args.date) or date.today()
    date_str = report_date.isoformat()
    dry_run = args.dry_run

    print(f"MovieTrace daily-discover for {date_str}")
    print(f"Dry-run: {dry_run}")
    print()

    secrets = _load_secrets()
    omdb_key = (secrets.get("omdb") or {}).get("api_key", "")
    tmdb_token = _load_tmdb_token()

    # Read FP config for movie scheduling
    cfg = _load_config()
    fp_cfg = cfg.get("flixpatrol", {})
    fetch_movies = args.force_fp_movies or False
    if not fetch_movies:
        fetch_movies = fp_cfg.get("movie_fetch_weekly", False)
    movie_weekly_day = fp_cfg.get("movie_weekly_day", 0)

    # Step 1: Fetch TMDb trending
    print("[1/6] Fetching TMDb trending...", end=" ", flush=True)
    try:
        from movietrace.pipeline.tmdb_trending import fetch_and_store_tmdb_trending
        tmdb_result = fetch_and_store_tmdb_trending(
            db_path="data/movietrace.db",
            bearer_token=tmdb_token,
            snapshot_date=date_str,
        )
        print(f"OK ({tmdb_result.get('inserted', 0)} items)")
    except Exception as exc:
        print(f"FAILED: {exc}")
        return 1

    # Step 3: Fetch Trakt trending
    print("[2/5] Fetching Trakt trending...", end=" ", flush=True)
    try:
        trakt_client_id = (secrets.get("trakt") or {}).get("client_id", "")
        if trakt_client_id:
            from movietrace.pipeline.trakt_trending import fetch_and_store_trakt_trending
            trakt_result = fetch_and_store_trakt_trending(
                db_path="data/movietrace.db",
                client_id=trakt_client_id,
                snapshot_date=date_str,
            )
            print(f"OK ({trakt_result.get('inserted', 0)} items)")
        else:
            print("SKIPPED (no Trakt client_id)")
    except Exception as exc:
        print(f"FAILED: {exc}")
        return 1

    # Step 4: Merge + Enrich + Score + Write
    print("[3/5] Merging + enriching...", end=" ", flush=True)
    try:
        from movietrace.pipeline.discovery import run_discovery
        result = run_discovery(
            date_from=date_str, dry_run=dry_run,
            fetch_movies=fetch_movies,
            movie_weekly_day=movie_weekly_day,
        )
        stats = result.get("stats", {})
        merged = stats.get("total_merged", 0)
        omdb_enrich = stats.get("enrich_omdb", {})
        print(f"OK (merged={merged} omdb_hit={omdb_enrich.get('enriched', 0)})")
    except Exception as exc:
        print(f"FAILED: {exc}")
        return 1

    # Step 5: Scoring + filtering
    print("[4/5] Scoring + filtering...", end=" ", flush=True)
    try:
        passed_count = stats.get("total_passed", 0)
        total_merged = stats.get("total_merged", 0)
        print(f"OK (passed P2+ = {passed_count} of {total_merged})")
    except Exception as exc:
        print(f"FAILED: {exc}")
        return 1

    # Step 6: Baseline tracking
    cfg = _load_config()
    bt_cfg = cfg.get("baseline_tracking", {})
    written = stats.get("written", 0)
    if bt_cfg.get("enabled", True):
        print(f"[5/5] Writing content_updates + baseline tracking...", end=" ", flush=True)
        try:
            from movietrace.pipeline.baseline_tracking import run_baseline_tracking
            bt_result = run_baseline_tracking(
                db_path="data/movietrace.db",
                tmdb_token=tmdb_token,
                dry_run=dry_run,
            )
            print(
                f"OK (written={written} + {bt_result.get('written', 0)} new_seasons)"
            )
        except Exception as exc:
            print(f"FAILED: {exc}")
            return 1
    else:
        print(f"[5/5] Writing content_updates... OK (written={written}, baseline skipped)")

    print()
    print(f"✓ Daily discovery complete (P0={stats.get('P0',0)} P1={stats.get('P1',0)} P2={stats.get('P2',0)})")
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
        print(f"  含季号 (S\\d\\d): {up_with_s}")
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


def _load_secrets(path: str = "/tmp/movietrace_phase0_secrets.json") -> dict:
    try:
        return json.loads(open(path).read())
    except (FileNotFoundError, json.JSONDecodeError):
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


# ── inspect-updates ─────────────────────────────────────────────────────


def cmd_inspect_updates(args: argparse.Namespace) -> int:
    """Query and display content_updates from local DB."""
    from movietrace.reports.inspect_renderer import (
        query_updates,
        format_table,
        format_detail,
        format_json_enhanced,
        format_markdown_enhanced,
    )

    days = args.days or 7
    fmt = args.format or "table"

    updates = query_updates(
        db_path="data/movietrace.db",
        days=days,
        priority=args.priority,
        update_type=getattr(args, "type", None),
        content_update_id=args.id,
    )

    if args.id:
        if updates:
            print(format_detail(updates[0]))
        else:
            print(f"No update found with id: {args.id}")
        return 0

    if fmt == "json":
        print(format_json_enhanced(updates))
    elif fmt == "md":
        from datetime import datetime
        ts = datetime.now().strftime("%Y-%m-%d_%H%M")
        path = f"reports/inspect_{ts}.md"
        content = format_markdown_enhanced(updates, days)
        from pathlib import Path
        Path("reports").mkdir(parents=True, exist_ok=True)
        Path(path).write_text(content, encoding="utf-8")
        print(f"Written to {path}")
    else:
        print(format_table(updates))

    return 0


def _parse_date_arg(date_str: str | None) -> date | None:
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        print(f"Invalid date format: {date_str}. Use YYYY-MM-DD.", file=sys.stderr)
        sys.exit(1)


# ── fetch-tmdb-trending ──────────────────────────────────────────────────


def cmd_fetch_tmdb_trending(args: argparse.Namespace) -> int:
    """Fetch TMDb trending/popular data and store in tmdb_trending table."""
    report_date = _parse_date_arg(args.date) or date.today()
    date_str = report_date.isoformat()

    print(f"MovieTrace fetch-tmdb-trending for {date_str}")
    print(f"Pages per endpoint: {args.pages}")
    print()

    try:
        from movietrace.pipeline.tmdb_trending import fetch_and_store_tmdb_trending

        tmdb_token = _load_tmdb_token()
        result = fetch_and_store_tmdb_trending(
            db_path="data/movietrace.db",
            bearer_token=tmdb_token,
            snapshot_date=date_str,
            pages_per_endpoint=args.pages,
        )

        print(f"Fetched:  {result.get('fetched', 0)}")
        print(f"Inserted: {result.get('inserted', 0)}")
        print(f"Errors:   {result.get('errors', 0)}")
        print()
        print("✓ TMDb trending fetch complete")
        return 0 if result.get("errors", 0) == 0 else 1
    except Exception as exc:
        print(f"✗ TMDb trending fetch failed: {exc}")
        return 1


# ── fetch-trakt-trending ─────────────────────────────────────────────────


def cmd_fetch_trakt_trending(args: argparse.Namespace) -> int:
    """Fetch Trakt trending data and store in trakt_trending table."""
    report_date = _parse_date_arg(args.date) or date.today()
    date_str = report_date.isoformat()

    print(f"MovieTrace fetch-trakt-trending for {date_str}")
    print()

    secrets_path = "/tmp/movietrace_phase0_secrets.json"
    try:
        secrets = json.loads(open(secrets_path).read())
    except FileNotFoundError:
        print(f"✗ Secrets file not found: {secrets_path}")
        return 1

    client_id = (secrets.get("trakt") or {}).get("client_id")
    if not client_id:
        print("✗ Trakt client_id not found in secrets file")
        return 1

    try:
        from movietrace.pipeline.trakt_trending import fetch_and_store_trakt_trending

        result = fetch_and_store_trakt_trending(
            db_path="data/movietrace.db",
            client_id=client_id,
            snapshot_date=date_str,
        )

        print(f"Fetched:  {result.get('fetched', 0)}")
        print(f"Inserted: {result.get('inserted', 0)}")
        print(f"Errors:   {result.get('errors', 0)}")
        print()
        print("✓ Trakt trending fetch complete")
        return 0 if result.get("errors", 0) == 0 else 1
    except Exception as exc:
        print(f"✗ Trakt trending fetch failed: {exc}")
        return 1


# ── inspect-api-usage ─────────────────────────────────────────────────────


def cmd_inspect_api_usage(args: argparse.Namespace) -> int:
    """Query and display API usage log from local DB."""
    conn = connect_database("data/movietrace.db")

    conditions: list[str] = []
    params: list = []

    if args.date:
        conditions.append("request_date = ?")
        params.append(args.date)
    if args.days:
        from datetime import date as dt_date, timedelta
        since = (dt_date.today() - timedelta(days=args.days)).isoformat()
        conditions.append("request_date >= ?")
        params.append(since)
    if args.service:
        conditions.append("service = ?")
        params.append(args.service)

    where = ""
    prefix = "WHERE"  # for sub-queries: "WHERE x AND y" or "WHERE status='success'"
    if conditions:
        where = " WHERE " + " AND ".join(conditions)
        prefix = "AND"

    # Summary query
    total = conn.execute(f"select count(*) from api_usage_log{where}", params).fetchone()[0]
    success = conn.execute(
        f"select count(*) from api_usage_log{where} {prefix} status='success'", params
    ).fetchone()[0]
    errors = conn.execute(
        f"select count(*) from api_usage_log{where} {prefix} status IN ('http_error','network_error')",
        params,
    ).fetchone()[0]
    quota = conn.execute(
        f"select count(*) from api_usage_log{where} {prefix} quota_error=1", params
    ).fetchone()[0]
    rate_limited = conn.execute(
        f"select count(*) from api_usage_log{where} {prefix} rate_limited=1", params
    ).fetchone()[0]

    fmt = args.format or "table"

    if fmt == "json":
        by_service = conn.execute(
            f"""select service, count(*) as cnt,
            sum(case when status='success' then 1 else 0 end) as success,
            sum(case when quota_error=1 then 1 else 0 end) as quota,
            sum(case when rate_limited=1 then 1 else 0 end) as rate_limited
            from api_usage_log{where} group by service order by cnt desc""",
            params,
        ).fetchall()
        by_endpoint = conn.execute(
            f"""select endpoint, count(*) as cnt
            from api_usage_log{where} group by endpoint order by cnt desc""",
            params,
        ).fetchall()

        import json
        output = {
            "total": total,
            "success": success,
            "errors": errors,
            "quota_errors": quota,
            "rate_limited": rate_limited,
            "by_service": [
                {"service": r[0], "total": r[1], "success": r[2], "quota": r[3], "rate_limited": r[4]}
                for r in by_service
            ],
            "by_endpoint": [
                {"endpoint": r[0], "count": r[1]} for r in by_endpoint
            ],
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        print(f"API Usage Summary")
        print(f"=================")
        print(f"  Total requests: {total}")
        print(f"  Success:        {success}")
        print(f"  Errors:         {errors}")
        print(f"  Quota errors:   {quota}")
        print(f"  Rate limited:   {rate_limited}")
        print()

        by_service = conn.execute(
            f"""select service, count(*) as cnt,
            sum(case when status='success' then 1 else 0 end) as success,
            sum(case when quota_error=1 then 1 else 0 end) as quota,
            sum(case when rate_limited=1 then 1 else 0 end) as rate_limited
            from api_usage_log{where} group by service order by cnt desc""",
            params,
        ).fetchall()
        if by_service:
            print("| Service    | Total | Success | Quota | Rate Limited |")
            print("|------------|-------|---------|-------|--------------|")
            for r in by_service:
                print(f"| {r[0]:10} | {r[1]:5} | {r[2]:7} | {r[3]:5} | {r[4]:12} |")
            print()

        by_endpoint = conn.execute(
            f"""select endpoint, count(*) as cnt
            from api_usage_log{where} group by endpoint order by cnt desc limit 20""",
            params,
        ).fetchall()
        if by_endpoint:
            print("| Endpoint                | Count |")
            print("|-------------------------|-------|")
            for r in by_endpoint:
                print(f"| {r[0]:23} | {r[1]:5} |")
            print()

    conn.close()
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="movietrace",
        description="MovieTrace Phase 1 CLI",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # daily-discover
    p_discover = sub.add_parser("daily-discover", help="Run full daily discovery pipeline")
    p_discover.add_argument("--date", help="Date in YYYY-MM-DD format")
    p_discover.add_argument("--dry-run", action="store_true", help="Skip write to DB")
    p_discover.add_argument("--force-fp-movies", action="store_true", help="Force FP movie fetch regardless of weekly schedule")

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

    # fetch-tmdb-trending
    p_tmdb = sub.add_parser("fetch-tmdb-trending", help="Fetch TMDb trending/popular data")
    p_tmdb.add_argument("--date", help="Date in YYYY-MM-DD format")
    p_tmdb.add_argument("--pages", type=int, default=3, help="Pages per endpoint (default: 3)")

    # fetch-trakt-trending
    p_trakt = sub.add_parser("fetch-trakt-trending", help="Fetch Trakt trending data")
    p_trakt.add_argument("--date", help="Date in YYYY-MM-DD format")

    # inspect-updates
    p_inspect_up = sub.add_parser("inspect-updates", help="Query and display content_updates")
    p_inspect_up.add_argument("--days", type=int, default=7, help="Days to cover (default: 7)")
    p_inspect_up.add_argument("--priority", help="Filter: P0,P1,P2")
    p_inspect_up.add_argument("--type", help="Filter: new_discovery, new_season, re_promotion")
    p_inspect_up.add_argument("--id", help="Show detail for specific content_update_id")
    p_inspect_up.add_argument("--format", choices=["table", "json", "md"], default="table")

    # inspect-api-usage
    p_api_usage = sub.add_parser("inspect-api-usage", help="Query API usage log")
    p_api_usage.add_argument("--date", help="Filter: YYYY-MM-DD")
    p_api_usage.add_argument("--days", type=int, help="Last N days")
    p_api_usage.add_argument("--service", help="Filter: tmdb, trakt, omdb, flixpatrol")
    p_api_usage.add_argument("--format", choices=["table", "json"], default="table")

    args = parser.parse_args()

    handlers = {
        "daily-discover": cmd_daily_discover,
        "validate-feishu": cmd_validate_feishu,
        "inspect-baseline": cmd_inspect_baseline,
        "check-feishu-schema": cmd_check_feishu_schema,
        "baseline-track": cmd_baseline_track,
        "export-recommendations": cmd_export_recommendations,
        "fetch-tmdb-trending": cmd_fetch_tmdb_trending,
        "fetch-trakt-trending": cmd_fetch_trakt_trending,
        "inspect-updates": cmd_inspect_updates,
        "inspect-api-usage": cmd_inspect_api_usage,
    }

    handler = handlers.get(args.command)
    if handler:
        sys.exit(handler(args))


if __name__ == "__main__":
    main()
