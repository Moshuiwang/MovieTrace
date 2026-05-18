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
import os
import sys
from pathlib import Path

from movietrace.config import load_secrets, get_secrets_path, get_db_path
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

    secrets = load_secrets()
    omdb_cfg = secrets.get("omdb") or {}
    omdb_keys = omdb_cfg.get("api_keys") or ([omdb_cfg.get("api_key")] if omdb_cfg.get("api_key") else [])
    tmdb_token = _load_tmdb_token()

    # Read FP config for movie scheduling
    cfg = _load_config()
    fp_cfg = cfg.get("flixpatrol", {})
    fetch_movies = args.force_fp_movies or False
    if not fetch_movies:
        fetch_movies = fp_cfg.get("movie_fetch_weekly", False)
    movie_weekly_day = fp_cfg.get("movie_weekly_day", 0)

    # Step 1: Fetch TMDb trending
    print("[1/5] Fetching TMDb trending...", end=" ", flush=True)
    tmdb_result = {}
    try:
        from movietrace.pipeline.tmdb_trending import fetch_and_store_tmdb_trending
        tmdb_pages = (cfg.get("source_fetch_limits") or {}).get("tmdb", {}).get("pages_per_endpoint", 1)
        tmdb_result = fetch_and_store_tmdb_trending(
            db_path=get_db_path(),
            bearer_token=tmdb_token,
            snapshot_date=date_str,
            pages_per_endpoint=tmdb_pages,
        )
        print(f"OK ({tmdb_result.get('inserted', 0)} items, {tmdb_pages}p)")
    except Exception as exc:
        print(f"FAILED: {exc}")
        tmdb_result = {"error": str(exc)}

    # Step 3: Fetch Trakt trending
    print("[2/5] Fetching Trakt trending...", end=" ", flush=True)
    trakt_result = {}
    try:
        trakt_client_id = (secrets.get("trakt") or {}).get("client_id", "")
        if trakt_client_id:
            from movietrace.pipeline.trakt_trending import fetch_and_store_trakt_trending
            trakt_limit_cfg = (cfg.get("source_fetch_limits") or {}).get("trakt", {})
            trakt_shows = trakt_limit_cfg.get("shows_limit", 20)
            trakt_movies = trakt_limit_cfg.get("movies_limit", 20)
            trakt_result = fetch_and_store_trakt_trending(
                db_path=get_db_path(),
                client_id=trakt_client_id,
                snapshot_date=date_str,
                shows_limit=trakt_shows,
                movies_limit=trakt_movies,
            )
            print(f"OK ({trakt_result.get('inserted', 0)} items, shows={trakt_shows} movies={trakt_movies})")
        else:
            print("SKIPPED (no Trakt client_id)")
    except Exception as exc:
        print(f"FAILED: {exc}")
        trakt_result = {"error": str(exc)}

    # Step 4: Merge + Enrich + Score + Write
    print("[3/5] Merging + enriching...", end=" ", flush=True)
    fallback_cfg = cfg.get("source_fallback")
    try:
        from movietrace.pipeline.discovery import run_discovery
        result = run_discovery(
            date_from=date_str, dry_run=dry_run,
            fetch_movies=fetch_movies,
            movie_weekly_day=movie_weekly_day,
            tmdb_fetch_result=tmdb_result,
            trakt_fetch_result=trakt_result,
            fallback_cfg=fallback_cfg,
        )
        stats = result.get("stats", {})
        merged = stats.get("total_merged", 0)
        omdb_enrich = stats.get("enrich_omdb", {})
        fallback_used = stats.get("source_fallback_used", False)
        fallback_note = " [FALLBACK]" if fallback_used else ""
        print(f"OK (merged={merged} omdb_hit={omdb_enrich.get('enriched', 0)}{fallback_note})")
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

    # Step 5: Write discovery updates only. Baseline tracking has its own cadence.
    written = stats.get("written", 0)
    print(f"[5/5] Writing content_updates... OK (written={written})")

    print()
    # Source data status (P1.10-D)
    source_status = stats.get("source_status", {})
    if source_status:
        print("Source data:")
        source_names = {"flixpatrol": "FlixPatrol", "tmdb": "TMDb", "trakt": "Trakt"}
        for src_key, src_label in source_names.items():
            ss = source_status.get(src_key, {})
            status = ss.get("status", "unknown")
            sdate = ss.get("snapshot_date")
            if status == "fresh":
                print(f"  {src_label}: fresh {sdate}")
            elif status == "fallback":
                print(f"  {src_label}: fallback from {sdate}")
            elif status == "failed_no_fallback":
                print(f"  {src_label}: failed_no_fallback")
            else:
                print(f"  {src_label}: {status}")
    print()
    print(f"✓ Daily discovery complete (P0={stats.get('P0',0)} P1={stats.get('P1',0)} P2={stats.get('P2',0)})")

    if getattr(args, "stats_out", None):
        discover_out = {
            "tmdb_fetched": tmdb_result.get("inserted", 0),
            "trakt_fetched": trakt_result.get("inserted", 0),
            "flixpatrol_fetched": 0,
            "total_merged": stats.get("total_merged", 0),
            "total_passed": stats.get("total_passed", 0),
            "written": stats.get("written", 0),
            "priority": {
                "P0": stats.get("P0", 0),
                "P1": stats.get("P1", 0),
                "P2": stats.get("P2", 0),
            },
            "source_status": stats.get("source_status", {}),
        }
        with open(args.stats_out, "w") as _f:
            json.dump(discover_out, _f, ensure_ascii=False, indent=2)
        print(f"Discover stats: {args.stats_out}")

    return 0


# ── validate-feishu ─────────────────────────────────────────────────────


def cmd_validate_feishu(args: argparse.Namespace) -> int:
    """Validate Feishu API connectivity and token."""
    secrets = load_secrets()
    if not secrets:
        print("✗ Secrets file not found:", get_secrets_path())
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
    conn = connect_database(get_db_path())
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

    secrets = load_secrets()
    if not secrets:
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


def _load_tmdb_token(secrets_path: str | None = None) -> str:
    secrets = load_secrets(secrets_path)
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
    print(f"Mode: {args.mode}")
    if args.limit:
        print(f"Limit: {args.limit}")
    print()

    try:
        from movietrace.pipeline.baseline_tracking import run_baseline_tracking

        tmdb_token = _load_tmdb_token()
        progress = None
        if not args.dry_run:
            def progress(index, total, item, cache_hit, detected):
                if index == 1 or index == total or index % 10 == 0:
                    source = "cache" if cache_hit else "api"
                    print(
                        f"Progress: {index}/{total} [{source}] "
                        f"{item.name} (tmdb={item.tmdb_tv_id}) detected={detected}",
                        flush=True,
                    )

        result = run_baseline_tracking(
            db_path=get_db_path(args.db),
            config=cfg,
            tmdb_token=tmdb_token,
            dry_run=args.dry_run,
            limit=args.limit,
            mode=args.mode,
            progress_callback=progress,
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
            db_path=get_db_path(args.db),
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


def cmd_export_baseline_updates(args: argparse.Namespace) -> int:
    """Export baseline new-season updates as separate MD + JSON report files."""
    print("MovieTrace export-baseline-updates")
    print(f"Days: {args.days}")
    print(f"Output dir: {args.output_dir}")
    print()

    try:
        from movietrace.reports.export_writer import export_baseline_updates

        result = export_baseline_updates(
            db_path=get_db_path(args.db),
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
        print("✓ Baseline export complete")
        return 0
    except Exception as exc:
        print(f"✗ Baseline export failed: {exc}")
        return 1


# ── Feishu credential helpers ─────────────────────────────────────────────


def _load_feishu_creds(secrets: dict) -> tuple[str, str, str] | None:
    """Extract (app_id, app_secret, base_app_token) from secrets dict. Returns None if any missing."""
    feishu = secrets.get("feishu", {})
    app_id = feishu.get("app_id")
    app_secret = feishu.get("app_secret")
    app_token = feishu.get("base_app_token")
    if not all([app_id, app_secret, app_token]):
        return None
    return app_id, app_secret, app_token


def _build_discovery_table_url(secrets: dict, app_token: str) -> str:
    """Build the Feishu bitable URL for the discovery table, or empty string if not configured."""
    table_id = (secrets.get("feishu") or {}).get("discovery_table_id", "")
    if not table_id or not app_token:
        return ""
    return f"https://my.feishu.cn/base/{app_token}?table={table_id}"


# ── sync-feishu-table ─────────────────────────────────────────────────────


def cmd_sync_feishu_table(args: argparse.Namespace) -> int:
    """Sync latest.json records to a Feishu bitable."""
    cfg = _load_config()
    fs_cfg = cfg.get("feishu_sync", {})
    if not fs_cfg.get("enabled", True):
        print("feishu_sync is disabled in config.yaml (enabled: false)")
        return 0

    secrets = load_secrets()
    creds = _load_feishu_creds(secrets)
    if creds is None:
        print("ERROR: feishu credentials (app_id, app_secret, base_app_token) not found in secrets.json")
        return 1
    app_id, app_secret, app_token = creds

    feishu_secrets = secrets.get("feishu") or {}
    table_id = feishu_secrets.get("discovery_table_id", "")
    if not table_id:
        print("ERROR: feishu.discovery_table_id not found in secrets.json")
        return 1

    notify_chat_id = feishu_secrets.get("notify_chat_id", "")

    print("MovieTrace sync-feishu-table")
    print(f"Source: {args.source}")
    print(f"Table ID: {table_id}")
    print(f"Dry-run: {args.dry_run}")
    print()

    try:
        from movietrace.feishu.sync import sync_table

        run_date = args.date or date.today().isoformat()

        stats = sync_table(
            json_path=args.source,
            run_date=run_date,
            app_id=app_id,
            app_secret=app_secret,
            app_token=app_token,
            table_id=table_id,
            dry_run=args.dry_run,
            notify_chat_id=notify_chat_id,
        )

        if stats.get("dry_run"):
            print("\n[DRY-RUN] 完成预览")
        else:
            print(f"\n同步完成: total={stats['total']}, created={stats['created']}, updated={stats['updated']}, errors={stats['errors']}")

        if getattr(args, "stats_out", None):
            sync_out = {
                "total": stats.get("total", 0),
                "created": stats.get("created", 0),
                "updated": stats.get("updated", 0),
                "errors": stats.get("errors", 0),
            }
            with open(args.stats_out, "w") as _f:
                json.dump(sync_out, _f, ensure_ascii=False, indent=2)
            print(f"Sync stats: {args.stats_out}")

        print("✓ sync-feishu-table complete")
        return 0 if stats.get("errors", 0) == 0 else 1
    except Exception as exc:
        print(f"✗ sync-feishu-table failed: {exc}")
        return 1


# ── setup-feishu-fields ──────────────────────────────────────────────────────


def cmd_setup_feishu_fields(args: argparse.Namespace) -> int:
    """幂等创建 P1.24 飞书发现运行日志表字段。"""
    secrets = load_secrets()
    creds = _load_feishu_creds(secrets)
    if creds is None:
        print("ERROR: feishu credentials (app_id, app_secret, base_app_token) not found in secrets.json")
        return 1
    app_id, app_secret, app_token = creds

    feishu_secrets = secrets.get("feishu") or {}
    table_id = feishu_secrets.get("discovery_table_id", "")
    if not table_id:
        print("ERROR: feishu.discovery_table_id not found in secrets.json")
        return 1

    print("MovieTrace setup-feishu-fields (P1.24)")
    print(f"Table ID: {table_id}")
    print(f"Dry-run: {args.dry_run}")
    print()

    try:
        from movietrace.feishu.schema_setup import ensure_table_fields

        result = ensure_table_fields(
            app_id=app_id,
            app_secret=app_secret,
            app_token=app_token,
            table_id=table_id,
            dry_run=args.dry_run,
        )

        created = result.get("created", [])
        existed = result.get("existed", [])
        renamed = result.get("renamed", [])
        errors = result.get("errors", [])

        if args.dry_run:
            print("[DRY-RUN] Plan:")
        else:
            print("Result:")

        if created:
            print(f"  Created: {len(created)} fields")
            for f in created:
                print(f"    - {f.get('field_name')} (type {f.get('field_type')})")

        if existed:
            print(f"  Existed: {len(existed)} fields")

        if renamed:
            print(f"  Renamed: {len(renamed)} fields")
            for r in renamed:
                print(f"    - {r.get('old_name')} → {r.get('new_name')}")

        if errors:
            print(f"  Errors: {len(errors)}")
            for e in errors:
                print(f"    - {e}")

        print()
        if errors:
            print("✗ setup-feishu-fields failed with errors")
            return 1
        else:
            print("✓ setup-feishu-fields complete")
            return 0
    except Exception as exc:
        print(f"✗ setup-feishu-fields failed: {exc}")
        return 1


# ── sync-feishu-doc ────────────────────────────────────────────────────────


def cmd_sync_feishu_doc(args: argparse.Namespace) -> int:
    """Sync latest.md as a Feishu document (via drive/v1/import_task)."""
    cfg = _load_config()
    fs_cfg = cfg.get("feishu_sync", {})
    if not fs_cfg.get("enabled", True):
        print("feishu_sync is disabled in config.yaml (enabled: false)")
        return 0

    target_type = fs_cfg.get("doc_import_type", "auto")

    secrets = load_secrets()
    folder_token = (secrets.get("feishu") or {}).get("doc_folder_token", "")
    if not folder_token:
        print("ERROR: feishu.doc_folder_token not found in secrets.json")
        return 1
    creds = _load_feishu_creds(secrets)
    if creds is None:
        print("ERROR: feishu credentials (app_id, app_secret, base_app_token) not found in secrets.json")
        return 1
    app_id, app_secret, _app_token = creds

    title = args.title or f"MovieTrace 每日发现 {date.today().isoformat()}"

    print("MovieTrace sync-feishu-doc")
    print(f"Source: {args.source}")
    print(f"Title: {title}")
    print(f"Target type: {target_type}")
    print(f"Dry-run: {args.dry_run}")
    print()

    try:
        from movietrace.feishu.sync import sync_doc

        result = sync_doc(
            md_path=args.source,
            title=title,
            folder_token=folder_token,
            app_id=app_id,
            app_secret=app_secret,
            dry_run=args.dry_run,
            target_type=target_type,
        )

        if result.get("dry_run"):
            print("\n[DRY-RUN] 完成预览")
        else:
            print(f"\nDoc URL: {result.get('doc_url', 'N/A')}")
            print(f"Doc token: {result.get('doc_token', 'N/A')}")

        print("✓ sync-feishu-doc complete")
        return 0
    except Exception as exc:
        print(f"✗ sync-feishu-doc failed: {exc}")
        return 1


# ── notify-feishu ──────────────────────────────────────────────────────────


def cmd_notify_feishu(args: argparse.Namespace) -> int:
    """Send a notification via Feishu bot."""
    cfg = _load_config()
    fs_cfg = cfg.get("feishu_sync", {})

    secrets = load_secrets()
    feishu_secrets = secrets.get("feishu") or {}

    # 优先使用外部群（secrets.json feishu.notify_chat_id），否则使用个人通知
    notify_chat_id = feishu_secrets.get("notify_chat_id", "")
    if notify_chat_id:
        receive_id = notify_chat_id
        receive_id_type = "chat_id"
    else:
        receive_id = feishu_secrets.get("notify_user_open_id", "")
        receive_id_type = "open_id"
        if not receive_id:
            print("ERROR: feishu.notify_chat_id 或 feishu.notify_user_open_id 未配置于 secrets.json")
            return 1

    creds = _load_feishu_creds(secrets)
    if creds is None:
        print("ERROR: feishu credentials (app_id, app_secret, base_app_token) not found in secrets.json")
        return 1
    app_id, app_secret, app_token = creds

    from movietrace.feishu.notify import send_summary, send_alert, send_card

    log_file = args.log_file or ""

    try:
        if args.level == "success":
            run_date = args.date or date.today().isoformat()

            discover_stats: dict = {}
            if getattr(args, "discover_stats_file", None):
                try:
                    with open(args.discover_stats_file) as f:
                        discover_stats = json.load(f)
                except Exception as e:
                    print(f"WARNING: could not read discover stats: {e}")

            sync_stats: dict = {}
            if args.stats_file:
                try:
                    with open(args.stats_file) as f:
                        sync_stats = json.load(f)
                except Exception as e:
                    print(f"WARNING: could not read sync stats: {e}")

            top_items: list = []
            if getattr(args, "report_file", None):
                try:
                    with open(args.report_file) as f:
                        report = json.load(f)
                    top_items = sorted(report, key=lambda x: x.get("hot_score", 0), reverse=True)
                except Exception as e:
                    print(f"WARNING: could not read report file: {e}")

            doc_url = args.doc_url or ""

            table_url = getattr(args, "table_url", "") or _build_discovery_table_url(secrets, app_token)

            if discover_stats:
                ok = send_card(
                    receive_id, run_date, discover_stats, sync_stats, top_items,
                    doc_url=doc_url, table_url=table_url, log_file=log_file,
                    app_id=app_id, app_secret=app_secret,
                    receive_id_type=receive_id_type,
                )
            else:
                ok = send_summary(
                    receive_id, run_date, sync_stats,
                    doc_url=doc_url, log_file=log_file,
                    app_id=app_id, app_secret=app_secret,
                    receive_id_type=receive_id_type,
                )
        else:
            ok = send_alert(
                receive_id,
                level=args.level,
                title=args.title or "MovieTrace 运行异常",
                detail=args.detail or "",
                log_file=log_file,
                app_id=app_id, app_secret=app_secret,
                receive_id_type=receive_id_type,
            )

        if ok:
            print("✓ notify-feishu sent")
        else:
            # Try Gmail fallback — credentials live in secrets.json → feishu.gmail
            gmail_cfg = feishu_secrets.get("gmail", {})
            if gmail_cfg.get("enabled"):
                from movietrace.feishu.notify import send_email
                sent = send_email(
                    smtp_user=gmail_cfg.get("smtp_user", ""),
                    smtp_password=gmail_cfg.get("smtp_password", ""),
                    to=gmail_cfg.get("smtp_user", ""),
                    subject=f"MovieTrace {args.level}: {args.title or 'Alert'}",
                    body=f"Level: {args.level}\nDetail: {args.detail or ''}\nLog: {log_file}",
                )
                if sent:
                    print("✓ Gmail fallback sent")
                    return 0

            print("✗ notify-feishu failed (and no fallback available)")
            return 1

        return 0
    except Exception as exc:
        print(f"✗ notify-feishu failed: {exc}")
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
        db_path=get_db_path(),
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

    cfg = _load_config()
    tmdb_limit_cfg = (cfg.get("source_fetch_limits") or {}).get("tmdb", {})
    pages = args.pages if args.pages is not None else tmdb_limit_cfg.get("pages_per_endpoint", 1)

    print(f"MovieTrace fetch-tmdb-trending for {date_str}")
    print(f"Pages per endpoint: {pages}")
    print()

    try:
        from movietrace.pipeline.tmdb_trending import fetch_and_store_tmdb_trending

        tmdb_token = _load_tmdb_token()
        result = fetch_and_store_tmdb_trending(
            db_path=get_db_path(),
            bearer_token=tmdb_token,
            snapshot_date=date_str,
            pages_per_endpoint=pages,
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

    cfg = _load_config()
    trakt_limit_cfg = (cfg.get("source_fetch_limits") or {}).get("trakt", {})
    shows_limit = args.shows_limit if args.shows_limit is not None else trakt_limit_cfg.get("shows_limit", 20)
    movies_limit = args.movies_limit if args.movies_limit is not None else trakt_limit_cfg.get("movies_limit", 20)

    print(f"MovieTrace fetch-trakt-trending for {date_str}")
    print(f"Shows limit: {shows_limit}, Movies limit: {movies_limit}")
    print()

    secrets = load_secrets()
    if not secrets:
        print(f"✗ Secrets file not found: {get_secrets_path()}")
        return 1

    client_id = (secrets.get("trakt") or {}).get("client_id")
    if not client_id:
        print("✗ Trakt client_id not found in secrets file")
        return 1

    try:
        from movietrace.pipeline.trakt_trending import fetch_and_store_trakt_trending

        result = fetch_and_store_trakt_trending(
            db_path=get_db_path(),
            client_id=client_id,
            snapshot_date=date_str,
            shows_limit=shows_limit,
            movies_limit=movies_limit,
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


# ── sync-feishu-gap-table ────────────────────────────────────────────────────


def cmd_sync_feishu_gap_table(args: argparse.Namespace) -> int:
    """Sync A库缺口 snapshot table to Feishu bitable.

    Reads current DB state directly (not content_updates events).
    Upsert key: TMDb ID.
    """
    cfg = _load_config()
    fs_cfg = cfg.get("feishu_sync", {})
    if not fs_cfg.get("enabled", True):
        print("feishu_sync is disabled in config.yaml (enabled: false)")
        return 0

    secrets = load_secrets()
    creds = _load_feishu_creds(secrets)
    if creds is None:
        print("ERROR: feishu credentials (app_id, app_secret, base_app_token) not found in secrets.json")
        return 1
    app_id, app_secret, app_token = creds

    feishu_secrets = secrets.get("feishu") or {}
    table_id = feishu_secrets.get("gap_table_id", "")
    if not table_id:
        print("ERROR: feishu.gap_table_id not found in secrets.json — run step 4 first")
        return 1

    print("MovieTrace sync-feishu-gap-table")
    print(f"Table ID: {table_id}")
    print(f"Dry-run: {args.dry_run}")
    print()

    try:
        from movietrace.feishu.gap_sync import compute_current_gaps, sync_gap_table
        from movietrace.db.schema import connect_database

        conn = connect_database(get_db_path(args.db))
        rows = compute_current_gaps(conn)
        conn.close()

        print(f"计算得 {len(rows)} 条缺口行")
        print()

        stats = sync_gap_table(
            rows,
            app_id=app_id,
            app_secret=app_secret,
            app_token=app_token,
            table_id=table_id,
            dry_run=args.dry_run,
        )

        if stats.get("dry_run"):
            print("\n[DRY-RUN] 完成预览")
        else:
            print(f"\n同步完成: total={stats['total']}, "
                  f"created={stats['created']}, updated={stats['updated']}, errors={stats['errors']}")

        print("✓ sync-feishu-gap-table complete")
        return 0 if stats.get("errors", 0) == 0 else 1
    except Exception as exc:
        print(f"✗ sync-feishu-gap-table failed: {exc}")
        return 1


# ── inspect-api-usage ─────────────────────────────────────────────────────


def cmd_inspect_api_usage(args: argparse.Namespace) -> int:
    """Query and display API usage log from local DB."""
    conn = connect_database(get_db_path())

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

    # Use WHERE 1=1 as stable base so all sub-queries can use AND freely.
    # Condition templates are hardcoded; all user values go through ? placeholders.
    where = " WHERE 1=1"
    if conditions:
        where = " WHERE " + " AND ".join(conditions)

    # Summary query
    total = conn.execute(f"select count(*) from api_usage_log{where}", params).fetchone()[0]
    success = conn.execute(
        f"select count(*) from api_usage_log{where} AND status='success'", params
    ).fetchone()[0]
    errors = conn.execute(
        f"select count(*) from api_usage_log{where} AND status IN ('http_error','network_error')",
        params,
    ).fetchone()[0]
    quota = conn.execute(
        f"select count(*) from api_usage_log{where} AND quota_error=1", params
    ).fetchone()[0]
    rate_limited = conn.execute(
        f"select count(*) from api_usage_log{where} AND rate_limited=1", params
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


# ── pull-feishu-feedback ──────────────────────────────────────────────────


def cmd_pull_feishu_feedback(args: argparse.Namespace) -> int:
    """Pull operator feedback from Feishu bitable tables."""
    cfg = _load_config()
    fs_cfg = cfg.get("feishu_sync", {})
    if not fs_cfg.get("enabled", True):
        print("feishu_sync is disabled in config.yaml (enabled: false)")
        return 0

    secrets = load_secrets()
    creds = _load_feishu_creds(secrets)
    if creds is None:
        print("ERROR: feishu credentials (app_id, app_secret, base_app_token) not found in secrets.json")
        return 1
    app_id, app_secret, app_token = creds

    feishu_secrets = secrets.get("feishu") or {}
    hot_table_id = feishu_secrets.get("discovery_table_id", "")
    gap_table_id = feishu_secrets.get("gap_table_id", "")
    if not hot_table_id or not gap_table_id:
        print("ERROR: feishu.discovery_table_id and feishu.gap_table_id required in secrets.json")
        return 1

    output_dir = args.output or "reports/feedback"
    days = args.days or 7
    dry_run = args.dry_run

    print("MovieTrace pull-feishu-feedback")
    print(f"Days: {days}, Output: {output_dir}, Dry-run: {dry_run}")
    print()

    try:
        from movietrace.feedback.pull import pull_all
        pull_all(
            app_id=app_id,
            app_secret=app_secret,
            app_token=app_token,
            hot_table_id=hot_table_id,
            gap_table_id=gap_table_id,
            days=days,
            output_dir=output_dir,
            dry_run=dry_run,
        )
        print("\n✓ pull-feishu-feedback complete")
        return 0
    except Exception as exc:
        print(f"\n✗ pull-feishu-feedback failed: {exc}")
        return 1


# ── export-feedback-report ────────────────────────────────────────────────


def cmd_export_feedback_report(args: argparse.Namespace) -> int:
    """Generate weekly markdown report from a Feishu pull JSON."""
    import json as _json

    input_path = args.input or "reports/feedback/feishu_pull_latest.json"
    output_dir = args.output or "reports/feedback"
    db_path = get_db_path(args.db)
    dry_run = args.dry_run

    print("MovieTrace export-feedback-report")
    print(f"Input: {input_path}, Output: {output_dir}, Dry-run: {dry_run}")
    print()

    try:
        pull_data = _json.loads(Path(input_path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"ERROR: input file not found: {input_path}")
        print("Run 'pull-feishu-feedback' first to generate the data file.")
        return 1
    except _json.JSONDecodeError as exc:
        print(f"ERROR: invalid JSON in {input_path}: {exc}")
        return 1

    try:
        from movietrace.feedback.weekly_report import generate_weekly_report
        generate_weekly_report(
            pull_data,
            db_path=db_path,
            output_dir=output_dir,
            dry_run=dry_run,
        )
        print("\n✓ export-feedback-report complete")
        return 0
    except Exception as exc:
        print(f"\n✗ export-feedback-report failed: {exc}")
        return 1


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="movietrace",
        description="MovieTrace Phase 1 CLI",
    )
    parser.add_argument("--smoke-test", action="store_true",
                        help="Use smoke-test Feishu base instead of production")
    sub = parser.add_subparsers(dest="command", required=True)

    # daily-discover
    p_discover = sub.add_parser("daily-discover", help="Run full daily discovery pipeline")
    p_discover.add_argument("--date", help="Date in YYYY-MM-DD format")
    p_discover.add_argument("--dry-run", action="store_true", help="Skip write to DB")
    p_discover.add_argument("--force-fp-movies", action="store_true", help="Force FP movie fetch regardless of weekly schedule")
    p_discover.add_argument("--stats-out", help="Write discover pipeline stats JSON to this path")

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
    p_track.add_argument(
        "--mode",
        choices=["routine", "catch-up"],
        default="routine",
        help="Tracking mode: routine status-filtered polling or one-time catch-up",
    )

    # export-recommendations
    p_export = sub.add_parser("export-recommendations", help="Export recommendations to MD+JSON")
    p_export.add_argument("--db", help="Database path")
    p_export.add_argument("--days", type=int, default=7, help="Days to cover (default: 7)")
    p_export.add_argument("--output-dir", default="reports", help="Output directory")
    p_export.add_argument("--dry-run", action="store_true")

    # export-baseline-updates
    p_export_baseline = sub.add_parser(
        "export-baseline-updates", help="Export baseline new-season updates to MD+JSON"
    )
    p_export_baseline.add_argument("--db", help="Database path")
    p_export_baseline.add_argument("--days", type=int, default=7, help="Days to cover (default: 7)")
    p_export_baseline.add_argument("--output-dir", default="reports", help="Output directory")
    p_export_baseline.add_argument("--dry-run", action="store_true")

    # fetch-tmdb-trending
    p_tmdb = sub.add_parser("fetch-tmdb-trending", help="Fetch TMDb trending/popular data")
    p_tmdb.add_argument("--date", help="Date in YYYY-MM-DD format")
    p_tmdb.add_argument("--pages", type=int, default=None, help="Pages per endpoint (default: from config or 1)")

    # fetch-trakt-trending
    p_trakt = sub.add_parser("fetch-trakt-trending", help="Fetch Trakt trending data")
    p_trakt.add_argument("--date", help="Date in YYYY-MM-DD format")
    p_trakt.add_argument("--shows-limit", type=int, default=None, help="Shows trending limit (default: from config or 20)")
    p_trakt.add_argument("--movies-limit", type=int, default=None, help="Movies trending limit (default: from config or 20)")

    # inspect-updates
    p_inspect_up = sub.add_parser("inspect-updates", help="Query and display content_updates")
    p_inspect_up.add_argument("--days", type=int, default=7, help="Days to cover (default: 7)")
    p_inspect_up.add_argument("--priority", help="Filter: P0,P1,P2")
    p_inspect_up.add_argument("--type", help="Filter: new_discovery, new_season, re_promotion")
    p_inspect_up.add_argument("--id", help="Show detail for specific content_update_id")
    p_inspect_up.add_argument("--format", choices=["table", "json", "md"], default="table")

    # sync-feishu-table
    p_sync = sub.add_parser("sync-feishu-table", help="Sync discovery results to Feishu bitable")
    p_sync.add_argument("--source", default="reports/latest.json", help="JSON source path")
    p_sync.add_argument("--date", help="Run date YYYY-MM-DD (default: today)")
    p_sync.add_argument("--dry-run", action="store_true")
    p_sync.add_argument("--stats-out", help="Write sync stats JSON to this path")

    # setup-feishu-fields (P1.24-D)
    p_setup = sub.add_parser("setup-feishu-fields", help="Create/rename Feishu discovery table fields (P1.24)")
    p_setup.add_argument("--dry-run", action="store_true", help="Print plan without calling Feishu API")

    # sync-feishu-doc
    p_doc = sub.add_parser("sync-feishu-doc", help="Sync Markdown report as Feishu doc")
    p_doc.add_argument("--source", default="reports/latest.md", help="Markdown source path")
    p_doc.add_argument("--title", help="Document title (default: auto-generated)")
    p_doc.add_argument("--dry-run", action="store_true")

    # notify-feishu
    p_notify = sub.add_parser("notify-feishu", help="Send Feishu notification")
    p_notify.add_argument("--level", choices=["success", "error", "warning"], default="success")
    p_notify.add_argument("--title", help="Notification title (for error/warning)")
    p_notify.add_argument("--detail", help="Error detail")
    p_notify.add_argument("--date", help="Run date YYYY-MM-DD")
    p_notify.add_argument("--discover-stats-file", help="JSON file with discover pipeline stats")
    p_notify.add_argument("--stats-file", help="JSON file with sync stats")
    p_notify.add_argument("--report-file", help="JSON report file for top items (latest.json)")
    p_notify.add_argument("--doc-url", help="Feishu doc URL to include")
    p_notify.add_argument("--table-url", help="Feishu bitable URL to include")
    p_notify.add_argument("--log-file", help="Local log file path")

    # inspect-api-usage
    p_api_usage = sub.add_parser("inspect-api-usage", help="Query API usage log")
    p_api_usage.add_argument("--date", help="Filter: YYYY-MM-DD")
    p_api_usage.add_argument("--days", type=int, help="Last N days")
    p_api_usage.add_argument("--service", help="Filter: tmdb, trakt, omdb, flixpatrol")
    p_api_usage.add_argument("--format", choices=["table", "json"], default="table")

    # sync-feishu-gap-table
    p_gap = sub.add_parser("sync-feishu-gap-table", help="Sync A库缺口 snapshot to Feishu bitable")
    p_gap.add_argument("--db", help="Database path")
    p_gap.add_argument("--dry-run", action="store_true")

    # pull-feishu-feedback
    p_pull_fb = sub.add_parser("pull-feishu-feedback", help="Pull operator feedback from Feishu tables")
    p_pull_fb.add_argument("--days", type=int, default=7, help="Days to cover for hot table (default: 7)")
    p_pull_fb.add_argument("--output", help="Output directory (default: reports/feedback)")
    p_pull_fb.add_argument("--dry-run", action="store_true")

    # export-feedback-report
    p_exp_fb = sub.add_parser("export-feedback-report", help="Generate weekly feedback report from JSON")
    p_exp_fb.add_argument("--input", help="Input JSON file (default: reports/feedback/feishu_pull_latest.json)")
    p_exp_fb.add_argument("--output", help="Output directory (default: reports/feedback)")
    p_exp_fb.add_argument("--db", help="Database path for title lookup (default: data/movietrace.db)")
    p_exp_fb.add_argument("--dry-run", action="store_true")

    args = parser.parse_args()

    if args.smoke_test:
        os.environ["MOVIETRACE_SMOKE"] = "1"

    handlers = {
        "daily-discover": cmd_daily_discover,
        "validate-feishu": cmd_validate_feishu,
        "inspect-baseline": cmd_inspect_baseline,
        "check-feishu-schema": cmd_check_feishu_schema,
        "baseline-track": cmd_baseline_track,
        "export-recommendations": cmd_export_recommendations,
        "export-baseline-updates": cmd_export_baseline_updates,
        "sync-feishu-table": cmd_sync_feishu_table,
        "setup-feishu-fields": cmd_setup_feishu_fields,
        "sync-feishu-doc": cmd_sync_feishu_doc,
        "notify-feishu": cmd_notify_feishu,
        "fetch-tmdb-trending": cmd_fetch_tmdb_trending,
        "fetch-trakt-trending": cmd_fetch_trakt_trending,
        "inspect-updates": cmd_inspect_updates,
        "inspect-api-usage": cmd_inspect_api_usage,
        "sync-feishu-gap-table": cmd_sync_feishu_gap_table,
        "pull-feishu-feedback": cmd_pull_feishu_feedback,
        "export-feedback-report": cmd_export_feedback_report,
    }

    handler = handlers.get(args.command)
    if handler:
        sys.exit(handler(args))


if __name__ == "__main__":
    main()
