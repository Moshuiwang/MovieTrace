#!/usr/bin/env python3
"""P1.24-G: 历史 content_updates 行的 source_summary 回填 last_episode_to_air。

零 TMDb API 调用：全部数据来自 api_cache:tmdb:detail:%:tv。

用法:
    PYTHONPATH=src python scripts/p1_24_backfill_in_play_season.py [--dry-run] [--days 30] [--db data/movietrace.db]

返回 stats JSON:
    {
        "scanned": 10,
        "updated": 5,
        "skipped_no_cache": 2,
        "skipped_movie": 1,
        "skipped_already_has": 1,
        "errors": 1,
        "dry_run": false
    }
"""

from __future__ import annotations

import argparse
import json
import logging
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from movietrace.db.schema import connect_database


def _extract_tmdb_tv_id(content_update_id: str) -> str | None:
    """Parse tmdb_tv_id from content_update_id.

    Supports:
      - discovery:tv:{tmdb_id}:{date}
      - new_season:{tmdb_tv_id}:{season}:{date}

    Returns None if format is invalid or not TV type.
    """
    if not content_update_id:
        return None

    parts = content_update_id.split(":")
    if len(parts) < 3:
        return None

    if parts[0] == "discovery" and parts[1] == "tv":
        return parts[2]
    if parts[0] == "new_season":
        return parts[1]

    return None


def backfill(
    db_path: str, *, days: int = 30, dry_run: bool = False, logger=None
) -> dict:
    """Scan content_updates table, extract last_episode_to_air from api_cache, merge into source_summary.

    Args:
        db_path: Path to movietrace.db
        days: Backfill only rows created in last N days (default 30)
        dry_run: If True, only print plan without writing to DB
        logger: Python logger instance (optional)

    Returns:
        stats dict: {scanned, updated, skipped_no_cache, skipped_movie, skipped_already_has, errors, dry_run}
    """
    conn = connect_database(db_path)
    try:
        # 1. Query rows to backfill (only TV new_discovery + new_season; movie not needed)
        rows = conn.execute(
            """select id, content_update_id, source_summary_json
               from content_updates
               where created_at >= datetime('now', ?)
                 and (content_update_id like 'discovery:tv:%' or update_type = 'new_season')
               order by created_at desc""",
            (f"-{days} days",),
        ).fetchall()

        stats = {
            "scanned": len(rows),
            "updated": 0,
            "skipped_no_cache": 0,
            "skipped_movie": 0,
            "skipped_already_has": 0,
            "errors": 0,
            "dry_run": dry_run,
        }

        for row_id, cuid, summary_json in rows:
            try:
                # Extract tmdb_tv_id
                tmdb_tv_id = _extract_tmdb_tv_id(cuid)
                if not tmdb_tv_id:
                    stats["errors"] += 1
                    if logger:
                        logger.warning("Cannot extract tmdb_tv_id from %s", cuid)
                    continue

                # Parse existing source_summary
                ss = {}
                if summary_json:
                    try:
                        ss = json.loads(summary_json)
                    except (ValueError, TypeError):
                        ss = {}

                # Already has last_episode_to_air → skip (idempotent)
                if ss.get("last_episode_to_air"):
                    stats["skipped_already_has"] += 1
                    continue

                # Read from api_cache
                cache_row = conn.execute(
                    """select response_json from api_cache
                       where source = ? and cache_key = ?""",
                    ("tmdb", f"tmdb:detail:{tmdb_tv_id}:tv"),
                ).fetchone()

                if not cache_row:
                    stats["skipped_no_cache"] += 1
                    if logger:
                        logger.warning(
                            "No api_cache for tmdb:detail:%s:tv (cuid=%s)",
                            tmdb_tv_id,
                            cuid,
                        )
                    continue

                try:
                    tmdb_detail = json.loads(cache_row[0])
                except (ValueError, TypeError):
                    stats["errors"] += 1
                    if logger:
                        logger.warning(
                            "Invalid JSON in api_cache for tmdb:detail:%s:tv",
                            tmdb_tv_id,
                        )
                    continue

                last_aired = tmdb_detail.get("last_episode_to_air")
                if not last_aired:
                    stats["skipped_no_cache"] += 1
                    if logger:
                        logger.debug(
                            "No last_episode_to_air in tmdb_detail for %s", cuid
                        )
                    continue

                # Merge: only write last_episode_to_air, other fields untouched
                ss["last_episode_to_air"] = last_aired
                new_summary = json.dumps(ss, ensure_ascii=False)

                if dry_run:
                    stats["updated"] += 1
                    if logger and stats["updated"] <= 5:
                        logger.info(
                            "[DRY] %s: last_aired.season=%s",
                            cuid,
                            last_aired.get("season_number"),
                        )
                    continue

                conn.execute(
                    "update content_updates set source_summary_json = ? where id = ?",
                    (new_summary, row_id),
                )
                stats["updated"] += 1

            except Exception as exc:
                stats["errors"] += 1
                if logger:
                    logger.warning("Failed to backfill %s: %s", cuid, exc)

        if not dry_run:
            conn.commit()

        return stats

    finally:
        conn.close()


def main(argv=None) -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="P1.24-G: Backfill last_episode_to_air season number for historical content_updates rows"
    )
    parser.add_argument(
        "--db", default="data/movietrace.db", help="Path to movietrace.db"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Backfill only rows created in last N days (default 30)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only print plan, do not write to DB",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    logger = logging.getLogger("p1.24-g")

    stats = backfill(args.db, days=args.days, dry_run=args.dry_run, logger=logger)
    print(json.dumps(stats, ensure_ascii=False, indent=2))

    return 0 if stats.get("errors", 0) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
