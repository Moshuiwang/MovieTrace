from __future__ import annotations

import logging
import sqlite3
import time
from datetime import date

from movietrace.db.schema import connect_database
from movietrace.sources.trakt import TraktTrendingClient, normalize_trakt_trending_row

logger = logging.getLogger("movietrace.pipeline.trakt_trending")


def fetch_and_store_trakt_trending(
    db_path: str,
    client_id: str,
    snapshot_date: str | None = None,
) -> dict:
    if snapshot_date is None:
        snapshot_date = date.today().isoformat()

    client = TraktTrendingClient(client_id)
    conn = connect_database(db_path)

    fetched = 0
    inserted = 0
    errors = 0

    endpoints = [
        ("fetch_shows_trending", "shows/trending"),
        ("fetch_movies_trending", "movies/trending"),
    ]

    try:
        for method_name, endpoint_name in endpoints:
            try:
                items = getattr(client, method_name)()
            except Exception as exc:
                logger.error("%s failed: %s", endpoint_name, exc)
                errors += 1
                continue

            for item in items:
                if not isinstance(item, dict):
                    continue
                row = normalize_trakt_trending_row(item, endpoint_name, snapshot_date)
                if row is None:
                    continue
                fetched += 1
                try:
                    cursor = conn.execute(
                        """insert or ignore into trakt_trending
                           (trakt_id, tmdb_id, imdb_id, media_type, title, year,
                            watchers, rating, votes, source_endpoint, snapshot_date,
                            raw_payload_json)
                           values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            row["trakt_id"], row["tmdb_id"], row["imdb_id"],
                            row["media_type"], row["title"], row["year"],
                            row["watchers"], row["rating"], row["votes"],
                            row["source_endpoint"], row["snapshot_date"],
                            row["raw_payload_json"],
                        ),
                    )
                    if cursor.rowcount > 0:
                        inserted += 1
                except Exception as exc:
                    logger.warning("Failed to insert trakt_trending row: %s", exc)
                    errors += 1

            time.sleep(1.0)  # polite between endpoints

        conn.commit()
    finally:
        conn.close()

    logger.info(
        "Trakt trending: fetched=%d inserted=%d errors=%d", fetched, inserted, errors
    )
    return {"fetched": fetched, "inserted": inserted, "errors": errors}
