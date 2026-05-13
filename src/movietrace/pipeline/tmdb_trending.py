from __future__ import annotations

import logging
import sqlite3
import time
from datetime import date

from movietrace.db.schema import connect_database
from movietrace.sources.tmdb import TmdbTrendingClient, normalize_tmdb_trending_row

logger = logging.getLogger("movietrace.pipeline.tmdb_trending")

ENDPOINTS = [
    ("fetch_trending_all_day", "trending/day"),
    ("fetch_tv_popular", "tv/popular"),
    ("fetch_movie_popular", "movie/popular"),
]


def fetch_and_store_tmdb_trending(
    db_path: str,
    bearer_token: str,
    snapshot_date: str | None = None,
    pages_per_endpoint: int = 3,
) -> dict:
    if snapshot_date is None:
        snapshot_date = date.today().isoformat()

    client = TmdbTrendingClient(bearer_token)
    conn = connect_database(db_path)

    fetched = 0
    inserted = 0
    errors = 0

    try:
        for method_name, endpoint_name in ENDPOINTS:
            fetch_method = getattr(client, method_name)
            for page in range(1, pages_per_endpoint + 1):
                try:
                    items = fetch_method(page=page)
                except Exception as exc:
                    logger.error("%s page %d failed: %s", endpoint_name, page, exc)
                    errors += 1
                    continue

                for item in items:
                    if not isinstance(item, dict):
                        continue
                    row = normalize_tmdb_trending_row(item, endpoint_name, page, snapshot_date)
                    if row is None:
                        continue
                    fetched += 1
                    try:
                        cursor = conn.execute(
                            """insert or ignore into tmdb_trending
                               (tmdb_id, media_type, title, original_title, release_date,
                                original_language, popularity, vote_average, vote_count,
                                source_endpoint, source_page, snapshot_date, raw_payload_json)
                               values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                            (
                                row["tmdb_id"], row["media_type"], row["title"],
                                row["original_title"], row["release_date"],
                                row["original_language"], row["popularity"],
                                row["vote_average"], row["vote_count"],
                                row["source_endpoint"], row["source_page"],
                                row["snapshot_date"], row["raw_payload_json"],
                            ),
                        )
                        if cursor.rowcount > 0:
                            inserted += 1
                    except Exception as exc:
                        logger.warning("Failed to insert tmdb_trending row: %s", exc)
                        errors += 1

                time.sleep(0.5)  # polite between pages

            time.sleep(1.0)  # polite between endpoints

        conn.commit()
    finally:
        conn.close()

    logger.info(
        "TMDb trending: fetched=%d inserted=%d errors=%d", fetched, inserted, errors
    )
    return {"fetched": fetched, "inserted": inserted, "errors": errors}
