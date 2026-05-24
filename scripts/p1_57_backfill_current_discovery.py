#!/usr/bin/env python3
"""P1.57c: Backfill current_discovery_items / discovery_observations from
historical content_updates.update_type='new_discovery' rows.

Usage:
    python scripts/p1_57_backfill_current_discovery.py [--db PATH] [--commit]

Default is dry-run. Pass --commit to write to the database.
A DB backup is created before any writes.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import datetime, date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

P142_CUTOFF = "2026-05-22"  # P1.42 (2026-05-22) fixed pure-fallback writes
DEFAULT_DB = ROOT / "data" / "movietrace.db"


def _parse_discovery_id(content_update_id: str) -> tuple[str, str, str] | None:
    """Parse old 'discovery:{movie|tv}:{tmdb_id}:{date}' format.

    Returns (content_type, tmdb_id_str, date_str) or None on parse failure.
    """
    if not content_update_id:
        return None
    parts = content_update_id.split(":")
    if len(parts) < 4:
        return None
    if parts[0] != "discovery":
        return None
    content_type = parts[1]
    if content_type not in ("movie", "tv"):
        return None
    tmdb_id_str = parts[2]
    if not tmdb_id_str.isdigit():
        return None
    # Date may be in index 3
    date_str = parts[3]
    # Validate date format YYYY-MM-DD
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        return None
    return content_type, tmdb_id_str, date_str


def _backup_db(db_path: Path) -> Path:
    """Create a timestamped backup of the database."""
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    backup_path = db_path.parent / f"movietrace_backup_{ts}_pre_p157c_backfill.db"
    shutil.copy2(db_path, backup_path)
    print(f"DB backup created: {backup_path}")
    return backup_path


def run_backfill(db_path: Path, commit: bool = False) -> dict:
    from movietrace.db.schema import connect_database
    from movietrace.pipeline.current_discovery import (
        build_discovery_key,
        upsert_current_discovery_item,
        upsert_discovery_observation,
    )

    conn = connect_database(db_path)
    try:
        # Load all new_discovery rows ordered by created_at ascending
        rows = conn.execute(
            """
            SELECT cu.content_update_id, cu.canonical_item_id, cu.priority,
                   cu.hot_score, cu.source_summary_json, cu.created_at,
                   ci.title, ci.original_title, ci.title_zh,
                   ci.content_type as canonical_content_type
            FROM content_updates cu
            LEFT JOIN canonical_items ci ON ci.id = cu.canonical_item_id
            WHERE cu.update_type = 'new_discovery'
            ORDER BY cu.created_at ASC
            """
        ).fetchall()

        stats = {
            "rows_read": len(rows),
            "current_items_created": 0,
            "current_items_updated": 0,
            "observations_written": 0,
            "observations_skipped_parse_error": 0,
            "observations_before_p142_cutoff": 0,
            "observations_after_p142_cutoff": 0,
            "errors": 0,
        }

        skipped_ids: list[str] = []
        # Group by stable key to track first/last/count
        item_tracker: dict[str, dict] = {}  # discovery_key → {dates: set, rows: list}

        for row in rows:
            cid = row[0]
            parsed = _parse_discovery_id(cid)
            if parsed is None:
                stats["observations_skipped_parse_error"] += 1
                skipped_ids.append(cid)
                continue

            content_type, tmdb_id_str, obs_date = parsed
            tmdb_id = int(tmdb_id_str)

            try:
                dkey = build_discovery_key(content_type, tmdb_id)
            except ValueError:
                stats["observations_skipped_parse_error"] += 1
                skipped_ids.append(cid)
                continue

            if dkey not in item_tracker:
                item_tracker[dkey] = {
                    "content_type": content_type,
                    "tmdb_id": tmdb_id,
                    "dates": set(),
                    "rows": [],
                    "canonical_item_id": row[1],
                    "title": row[6],
                    "original_title": row[7],
                    "title_zh": row[8],
                }

            entry = item_tracker[dkey]
            entry["dates"].add(obs_date)
            entry["rows"].append(row)
            # Use latest row for metadata
            entry["latest_row"] = row

        if commit:
            _backup_db(db_path)

        # A1: 按 item 提交策略（per-item commit）。
        # 选择理由：backfill 是一次性操作，一条 item 失败不应阻塞其他 item 的持久化；
        # 按 item 提交可让已成功的 item 立即落库，失败的 item 单独 rollback，
        # 便于排查后重跑而不影响已有数据。
        for dkey, entry in item_tracker.items():
            dates = sorted(entry["dates"])
            first_date = dates[0]
            last_date = dates[-1]

            # Count unique observation days
            all_rows = entry["rows"]
            # Get rows by date for observation upsert
            rows_by_date: dict[str, list] = {}
            for r in all_rows:
                parsed2 = _parse_discovery_id(r[0])
                if parsed2 is None:
                    continue
                _, _, obs_date = parsed2
                if obs_date not in rows_by_date:
                    rows_by_date[obs_date] = []
                rows_by_date[obs_date].append(r)

            # Use the latest row's data for current item
            latest_row = entry["latest_row"]
            hot_score = latest_row[3]
            priority = latest_row[2]
            source_summary_str = latest_row[4]
            source_summary = None
            if source_summary_str:
                try:
                    source_summary = json.loads(source_summary_str)
                except (ValueError, TypeError):
                    pass

            if commit:
                try:
                    # Check if item already exists to track created vs updated
                    existing = conn.execute(
                        "SELECT id FROM current_discovery_items WHERE discovery_key=?",
                        (dkey,),
                    ).fetchone()
                    was_new = existing is None

                    # We need to set the first and last dates correctly.
                    # upsert_current_discovery_item uses observed_date for last_discovered_date.
                    # We call it twice: once with first_date (to set first_discovered_date),
                    # then once per additional date to increment count.
                    # Actually, we need a different approach for backfill:
                    # Insert with explicit first_discovered_date.
                    conn.execute(
                        """
                        INSERT INTO current_discovery_items (
                            discovery_key, content_type, tmdb_id, canonical_item_id,
                            title, original_title, title_zh,
                            first_discovered_date, last_discovered_date, discovery_count,
                            latest_hot_score, latest_priority, latest_source_summary_json
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(discovery_key) DO UPDATE SET
                            last_discovered_date = CASE
                                WHEN excluded.last_discovered_date > last_discovered_date
                                THEN excluded.last_discovered_date
                                ELSE last_discovered_date
                            END,
                            discovery_count = CASE
                                WHEN excluded.discovery_count > discovery_count
                                THEN excluded.discovery_count
                                ELSE discovery_count
                            END,
                            latest_hot_score = excluded.latest_hot_score,
                            latest_priority = excluded.latest_priority,
                            latest_source_summary_json = excluded.latest_source_summary_json,
                            canonical_item_id = COALESCE(excluded.canonical_item_id, canonical_item_id),
                            title = COALESCE(excluded.title, title),
                            original_title = COALESCE(excluded.original_title, original_title),
                            title_zh = COALESCE(excluded.title_zh, title_zh),
                            updated_at = current_timestamp
                        """,
                        (
                            dkey, entry["content_type"], entry["tmdb_id"],
                            entry["canonical_item_id"],
                            entry["title"], entry["original_title"], entry["title_zh"],
                            first_date, last_date, len(dates),
                            hot_score, priority,
                            json.dumps(source_summary, ensure_ascii=False) if source_summary else None,
                        ),
                    )

                    if was_new:
                        stats["current_items_created"] += 1
                    else:
                        stats["current_items_updated"] += 1

                    # Write one observation per unique date
                    for obs_date in dates:
                        date_rows = rows_by_date.get(obs_date, [])
                        # Use the last row for this date (most recent)
                        best_row = date_rows[-1] if date_rows else None
                        if best_row:
                            obs_ss_str = best_row[4]
                            obs_ss = None
                            if obs_ss_str:
                                try:
                                    obs_ss = json.loads(obs_ss_str)
                                except (ValueError, TypeError):
                                    pass
                            obs_breakdown = (obs_ss or {}).get("score_breakdown")
                            obs_source_status = (obs_ss or {}).get("source_data_status")

                            conn.execute(
                                """
                                INSERT INTO discovery_observations (
                                    discovery_key, observed_date, hot_score, priority,
                                    source_summary_json, score_breakdown_json, source_status_json
                                )
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                                ON CONFLICT(discovery_key, observed_date) DO UPDATE SET
                                    hot_score = excluded.hot_score,
                                    priority = excluded.priority,
                                    source_summary_json = excluded.source_summary_json,
                                    score_breakdown_json = excluded.score_breakdown_json,
                                    source_status_json = excluded.source_status_json,
                                    updated_at = current_timestamp
                                """,
                                (
                                    dkey, obs_date, best_row[3], best_row[2],
                                    obs_ss_str,
                                    json.dumps(obs_breakdown, ensure_ascii=False) if obs_breakdown else None,
                                    json.dumps(obs_source_status, ensure_ascii=False) if obs_source_status else None,
                                ),
                            )
                            stats["observations_written"] += 1
                            if obs_date < P142_CUTOFF:
                                stats["observations_before_p142_cutoff"] += 1
                            else:
                                stats["observations_after_p142_cutoff"] += 1

                    # Per-item commit: persist this item's writes immediately.
                    # A failure in a later item won't affect already-committed items.
                    conn.commit()

                except Exception as exc:
                    # Rollback only the current item's uncommitted writes.
                    conn.rollback()
                    stats["errors"] += 1
                    print(f"  ERROR processing {dkey}: {exc}")
                    continue

            else:
                # dry-run: count what would happen
                existing = conn.execute(
                    "SELECT id FROM current_discovery_items WHERE discovery_key=?",
                    (dkey,),
                ).fetchone()
                if existing is None:
                    stats["current_items_created"] += 1
                else:
                    stats["current_items_updated"] += 1
                for obs_date in dates:
                    stats["observations_written"] += 1
                    if obs_date < P142_CUTOFF:
                        stats["observations_before_p142_cutoff"] += 1
                    else:
                        stats["observations_after_p142_cutoff"] += 1

        # A1: Per-item commit: each item is committed individually in the loop above.
        # No final bulk commit needed here.

        # Verify new_season rows untouched
        ns_count = conn.execute(
            "SELECT count(*) FROM content_updates WHERE update_type='new_season'"
        ).fetchone()[0]
        stats["new_season_rows_preserved"] = ns_count

        # Sample of skipped IDs for diagnostics
        if skipped_ids:
            stats["skipped_sample"] = skipped_ids[:10]

        return stats

    finally:
        conn.close()


def print_stats(stats: dict, commit: bool) -> None:
    mode = "COMMIT" if commit else "DRY-RUN"
    print(f"\n{'='*50}")
    print(f"P1.57c Backfill Results [{mode}]")
    print(f"{'='*50}")
    print(f"  rows_read:                      {stats['rows_read']}")
    print(f"  current_items_created:          {stats['current_items_created']}")
    print(f"  current_items_updated:          {stats['current_items_updated']}")
    print(f"  observations_written:           {stats['observations_written']}")
    print(f"  observations_skipped (parse):   {stats['observations_skipped_parse_error']}")
    print(f"  observations_before_p142:       {stats['observations_before_p142_cutoff']}")
    print(f"    (may include pure-fallback rows written before P1.42)")
    print(f"  observations_after_p142:        {stats['observations_after_p142_cutoff']}")
    print(f"  new_season_rows_preserved:      {stats.get('new_season_rows_preserved', 'N/A')}")
    print(f"  errors:                         {stats['errors']}")
    if stats.get("skipped_sample"):
        print(f"  skipped_sample (first 10):      {stats['skipped_sample']}")
    if commit:
        print("\n✅ Database updated.")
    else:
        print("\n[DRY-RUN] No changes made. Pass --commit to write.")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Backfill current_discovery_items / discovery_observations from content_updates"
    )
    parser.add_argument(
        "--db", type=Path, default=DEFAULT_DB,
        help=f"Path to SQLite DB (default: {DEFAULT_DB})",
    )
    parser.add_argument(
        "--commit", action="store_true",
        help="Write to database (default is dry-run)",
    )
    args = parser.parse_args()

    if not args.db.exists():
        print(f"ERROR: DB file not found: {args.db}", file=sys.stderr)
        return 1

    print(f"DB: {args.db}")
    print(f"Mode: {'COMMIT' if args.commit else 'DRY-RUN'}")
    print(f"P1.42 cutoff for stats: {P142_CUTOFF}")

    stats = run_backfill(args.db, commit=args.commit)
    print_stats(stats, args.commit)
    return 0 if stats["errors"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
