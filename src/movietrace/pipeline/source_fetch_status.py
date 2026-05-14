from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timedelta, timezone

logger = logging.getLogger("movietrace.pipeline.source_fetch_status")

VALID_STATUSES = {"fresh", "fallback", "failed_no_fallback", "skipped"}
VALID_SOURCES = {"flixpatrol", "tmdb", "trakt"}


def record_source_fetch_run(
    conn: sqlite3.Connection,
    target_date: str,
    source: str,
    status: str,
    *,
    source_snapshot_date: str | None = None,
    rows_fetched: int | None = None,
    rows_inserted: int | None = None,
    rows_used: int | None = None,
    error_message: str | None = None,
    config_json: str | None = None,
) -> None:
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid status: {status}, must be one of {VALID_STATUSES}")
    if source not in VALID_SOURCES:
        raise ValueError(f"Invalid source: {source}, must be one of {VALID_SOURCES}")

    conn.execute(
        """insert into source_fetch_runs
           (target_date, source, status, source_snapshot_date,
            rows_fetched, rows_inserted, rows_used,
            error_message, config_json, finished_at)
           values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
           on conflict(target_date, source) do update set
           status = excluded.status,
           source_snapshot_date = excluded.source_snapshot_date,
           rows_fetched = excluded.rows_fetched,
           rows_inserted = excluded.rows_inserted,
           rows_used = excluded.rows_used,
           error_message = excluded.error_message,
           config_json = excluded.config_json,
           updated_at = current_timestamp,
           finished_at = excluded.finished_at""",
        (
            target_date, source, status, source_snapshot_date,
            rows_fetched, rows_inserted, rows_used,
            error_message, config_json,
            datetime.now(timezone.utc).isoformat(),
        ),
    )


def get_source_fetch_runs(
    conn: sqlite3.Connection,
    target_date: str | None = None,
    source: str | None = None,
) -> list[dict]:
    query = "select * from source_fetch_runs where 1=1"
    params: list = []

    if target_date:
        query += " and target_date = ?"
        params.append(target_date)
    if source:
        query += " and source = ?"
        params.append(source)

    query += " order by target_date desc, source"
    original_factory = conn.row_factory
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(query, params).fetchall()
    finally:
        conn.row_factory = original_factory
    return [dict(row) for row in rows]


def find_latest_source_snapshot(
    conn: sqlite3.Connection,
    source: str,
    before_date: str,
    max_staleness_days: int = 30,
) -> str | None:
    max_staleness_date = (
        datetime.strptime(before_date, "%Y-%m-%d") - timedelta(days=max_staleness_days)
    ).strftime("%Y-%m-%d")

    # Look for a successful run (fresh or fallback) within staleness window
    row = conn.execute(
        """select source_snapshot_date from source_fetch_runs
           where source = ? and target_date < ?
           and target_date >= ?
           and status in ('fresh', 'fallback')
           and source_snapshot_date is not null
           order by target_date desc
           limit 1""",
        (source, before_date, max_staleness_date),
    ).fetchone()

    if row:
        return row[0]

    return None

