"""P1.57b current discovery / observation read-write helpers.

Stable key format: discovery:{movie|tv}:{tmdb_id}

Rules:
- Caller controls transaction boundary; helpers never commit.
- JSON fields serialized with json.dumps(..., ensure_ascii=False).
- Invalid content_type or missing tmdb_id raises ValueError immediately.
"""
from __future__ import annotations

import json
import sqlite3


def build_discovery_key(content_type: str, tmdb_id: int | str) -> str:
    """Build stable discovery key: discovery:{movie|tv}:{tmdb_id}."""
    if content_type not in ("movie", "tv"):
        raise ValueError(f"Invalid content_type: {content_type!r}. Must be 'movie' or 'tv'.")
    if not tmdb_id:
        raise ValueError("tmdb_id is required and must be non-empty.")
    return f"discovery:{content_type}:{tmdb_id}"


def upsert_current_discovery_item(
    conn: sqlite3.Connection,
    *,
    discovery_key: str,
    content_type: str,
    tmdb_id: int,
    observed_date: str,
    canonical_item_id: int | None = None,
    hot_score: float | None = None,
    priority: str | None = None,
    source_summary: dict | None = None,
    baseline_match_status: str | None = None,
    match_confidence_low: int = 0,
    stable_metadata: dict | None = None,
    title: str | None = None,
    original_title: str | None = None,
    title_zh: str | None = None,
) -> None:
    """Upsert a current discovery item.

    First write: INSERT with discovery_count=1, first_discovered_date=observed_date.
    Subsequent writes on same date: update scores/metadata, keep count.
    Subsequent writes on new date: update scores/metadata, increment count.

    Ordering assumption: this function assumes observed_date is monotonically
    non-decreasing across calls for the same discovery_key.  If the caller
    invokes with out-of-order dates (e.g. replaying old observations in random
    order), discovery_count may undercount because the CASE expression only
    increments when excluded.last_discovered_date > last_discovered_date.
    Production daily-discover and the backfill script both guarantee ascending
    date order, so this is safe in practice.
    """
    if content_type not in ("movie", "tv"):
        raise ValueError(f"Invalid content_type: {content_type!r}.")
    if not tmdb_id:
        raise ValueError("tmdb_id is required.")

    source_summary_json = (
        json.dumps(source_summary, ensure_ascii=False) if source_summary is not None else None
    )
    stable_metadata_json = (
        json.dumps(stable_metadata, ensure_ascii=False) if stable_metadata is not None else None
    )

    conn.execute(
        """
        INSERT INTO current_discovery_items (
            discovery_key, content_type, tmdb_id, canonical_item_id,
            title, original_title, title_zh,
            first_discovered_date, last_discovered_date, discovery_count,
            latest_hot_score, latest_priority, latest_baseline_match_status,
            latest_match_confidence_low, latest_source_summary_json, stable_metadata_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(discovery_key) DO UPDATE SET
            canonical_item_id = COALESCE(excluded.canonical_item_id, canonical_item_id),
            title = COALESCE(excluded.title, title),
            original_title = COALESCE(excluded.original_title, original_title),
            title_zh = COALESCE(excluded.title_zh, title_zh),
            last_discovered_date = CASE
                WHEN excluded.last_discovered_date > last_discovered_date
                THEN excluded.last_discovered_date
                ELSE last_discovered_date
            END,
            discovery_count = CASE
                WHEN excluded.last_discovered_date > last_discovered_date
                THEN discovery_count + 1
                ELSE discovery_count
            END,
            latest_hot_score = excluded.latest_hot_score,
            latest_priority = excluded.latest_priority,
            latest_baseline_match_status = excluded.latest_baseline_match_status,
            latest_match_confidence_low = excluded.latest_match_confidence_low,
            latest_source_summary_json = excluded.latest_source_summary_json,
            stable_metadata_json = COALESCE(excluded.stable_metadata_json, stable_metadata_json),
            updated_at = current_timestamp
        """,
        (
            discovery_key, content_type, tmdb_id, canonical_item_id,
            title, original_title, title_zh,
            observed_date, observed_date,
            hot_score, priority, baseline_match_status, match_confidence_low,
            source_summary_json, stable_metadata_json,
        ),
    )


def upsert_discovery_observation(
    conn: sqlite3.Connection,
    *,
    discovery_key: str,
    observed_date: str,
    hot_score: float | None = None,
    priority: str | None = None,
    source_summary: dict | None = None,
    raw_inputs: dict | None = None,
    score_breakdown: dict | None = None,
    source_status: dict | None = None,
) -> None:
    """Insert or update a discovery observation for (discovery_key, observed_date)."""
    source_summary_json = (
        json.dumps(source_summary, ensure_ascii=False) if source_summary is not None else None
    )
    raw_inputs_json = (
        json.dumps(raw_inputs, ensure_ascii=False) if raw_inputs is not None else None
    )
    score_breakdown_json = (
        json.dumps(score_breakdown, ensure_ascii=False) if score_breakdown is not None else None
    )
    source_status_json = (
        json.dumps(source_status, ensure_ascii=False) if source_status is not None else None
    )

    conn.execute(
        """
        INSERT INTO discovery_observations (
            discovery_key, observed_date, hot_score, priority,
            source_summary_json, raw_inputs_json, score_breakdown_json, source_status_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(discovery_key, observed_date) DO UPDATE SET
            hot_score = excluded.hot_score,
            priority = excluded.priority,
            source_summary_json = excluded.source_summary_json,
            raw_inputs_json = excluded.raw_inputs_json,
            score_breakdown_json = excluded.score_breakdown_json,
            source_status_json = excluded.source_status_json,
            updated_at = current_timestamp
        """,
        (
            discovery_key, observed_date, hot_score, priority,
            source_summary_json, raw_inputs_json, score_breakdown_json, source_status_json,
        ),
    )


def get_stable_metadata(conn: sqlite3.Connection, discovery_key: str) -> dict | None:
    """Return the parsed stable_metadata_json for a discovery key, or None if not found/NULL.

    Read-only helper for B2 enrichment-skip stable_metadata fallback.
    Never writes to the database.
    """
    row = conn.execute(
        "SELECT stable_metadata_json FROM current_discovery_items WHERE discovery_key = ?",
        (discovery_key,),
    ).fetchone()
    if row is None or row[0] is None:
        return None
    try:
        return json.loads(row[0])
    except (ValueError, TypeError):
        return None


def get_current_discovery_item(conn: sqlite3.Connection, discovery_key: str) -> dict | None:
    """Return the current discovery item as a dict, or None if not found."""
    cursor = conn.execute(
        "SELECT * FROM current_discovery_items WHERE discovery_key = ?",
        (discovery_key,),
    )
    row = cursor.fetchone()
    if row is None:
        return None
    cols = [d[0] for d in cursor.description]
    return dict(zip(cols, row))


def get_current_discovery_item_by_tmdb(
    conn: sqlite3.Connection, content_type: str, tmdb_id: int | str
) -> dict | None:
    """Return the current discovery item for (content_type, tmdb_id), or None."""
    discovery_key = build_discovery_key(content_type, tmdb_id)
    return get_current_discovery_item(conn, discovery_key)
