#!/usr/bin/env python3
"""P1.28: 历史 canonical_items 回填 zh-CN 字段（title_zh / overview_zh / genres_json / networks_json）。

从 TMDb zh-CN API 抓取数据写入 canonical_items；genres/networks 从 en-US detail 提取。
使用 api_cache 避免重复 API 调用。

用法:
    PYTHONPATH=src python scripts/p1_28_backfill_zh_fields.py [--dry-run] [--limit N] [--db DB_PATH]
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

from movietrace.config import load_secrets
from movietrace.db.schema import connect_database
from movietrace.pipeline.omdb_enrichment import (
    _fetch_zh_detail_with_cache,
    _update_canonical_zh_fields,
)
from movietrace.pipeline.tmdb_detail_cache import get_tmdb_detail_with_cache
from movietrace.sources.tmdb import TmdbDetailClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def backfill(db_path: str, limit: int | None, dry_run: bool, bearer_token: str) -> dict:
    conn = connect_database(db_path)
    client = TmdbDetailClient(bearer_token, db_path=db_path)

    rows = conn.execute(
        """select ci.id, ci.title, ci.content_type,
                  ei.external_id
           from canonical_items ci
           join external_ids ei on ei.canonical_item_id = ci.id and ei.source = 'tmdb'
           where ei.external_id like 'tv:%' or ei.external_id like 'movie:%'
           order by ci.id"""
    ).fetchall()

    if limit:
        rows = rows[:limit]

    stats = {"total": len(rows), "updated": 0, "skipped_no_data": 0, "errors": 0, "dry_run": dry_run}

    for canonical_id, title, content_type, ext_id in rows:
        try:
            parts = ext_id.split(":", 1)
            if len(parts) != 2:
                stats["skipped_no_data"] += 1
                continue
            media_type, tmdb_id_str = parts[0], parts[1]

            # Get en-US detail (uses cache; falls back to API if cache miss)
            en_data, _ = get_tmdb_detail_with_cache(conn, client, tmdb_id_str, media_type)
            genres_json = None
            networks_json = None
            if en_data:
                genres = en_data.get("genres")
                genres_json = json.dumps(genres, ensure_ascii=False) if isinstance(genres, list) else None
                networks = en_data.get("networks") if media_type == "tv" else None
                networks_json = json.dumps(networks, ensure_ascii=False) if isinstance(networks, list) else None

            # Get zh-CN detail
            zh_data, zh_cached = _fetch_zh_detail_with_cache(conn, client, tmdb_id_str, media_type)

            title_zh = None
            overview_zh = None
            if zh_data:
                raw_title = zh_data.get("name") or zh_data.get("title")
                raw_overview = zh_data.get("overview")
                title_zh = str(raw_title).strip() if raw_title else None
                overview_zh = str(raw_overview).strip() if raw_overview else None

            if dry_run:
                logger.info("[DRY] %s (%s): title_zh=%s genres=%s", title, ext_id, title_zh, genres_json)
                stats["updated"] += 1
                continue

            if _update_canonical_zh_fields(conn, tmdb_id_str, media_type, title_zh, overview_zh, genres_json, networks_json):
                stats["updated"] += 1
                logger.info("Updated %s (%s): title_zh=%s", title, ext_id, title_zh)
            else:
                stats["skipped_no_data"] += 1

        except Exception as exc:
            logger.error("Error processing canonical_id=%s (%s): %s", canonical_id, ext_id, exc)
            stats["errors"] += 1

    conn.close()
    return stats


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="data/movietrace.db")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    secrets = load_secrets()
    bearer_token = (secrets.get("tmdb") or {}).get("api_read_access_token", "")
    if not bearer_token:
        print("ERROR: tmdb.api_read_access_token not configured in secrets")
        return 1

    stats = backfill(args.db, limit=args.limit, dry_run=args.dry_run, bearer_token=bearer_token)
    print(json.dumps(stats, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
