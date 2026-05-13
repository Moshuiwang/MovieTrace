from __future__ import annotations

import json
import logging
import sqlite3
import time
from datetime import datetime, timedelta, timezone

from movietrace.pipeline.multi_source_merge import MergedCandidate
from movietrace.sources.omdb import OmdbDetailClient, format_imdb_id
from movietrace.sources.tmdb import TmdbDetailClient

logger = logging.getLogger("movietrace.pipeline.omdb_enrichment")


def backfill_imdb_ids(
    candidates: list[MergedCandidate],
    bearer_token: str,
    *,
    db_path: str = "data/movietrace.db",
    request_date: str = "",
) -> dict:
    """P1.8-F/G: Pre-score IMDb ID backfill via TMDb external_ids.

    For candidates with tmdb_id but no imdb_id, fetch the IMDb ID
    from TMDb's external_ids endpoint. Caches results in api_cache.
    Returns {"api_calls": int, "backfilled": int}.
    """
    client = TmdbDetailClient(bearer_token, db_path=db_path, request_date=request_date)
    api_calls = 0
    backfilled = 0

    for c in candidates:
        if c.imdb_id or not c.tmdb_id:
            continue
        try:
            imdb_id = client.fetch_imdb_id(c.tmdb_id, c.media_type)
            api_calls += 1
            if imdb_id:
                c.imdb_id = format_imdb_id(imdb_id)
                backfilled += 1
        except Exception as exc:
            logger.warning(
                "Failed to backfill IMDb ID for tmdb_id=%s: %s", c.tmdb_id, exc
            )

    logger.info(
        "IMDb backfill: api_calls=%d backfilled=%d of %d candidates",
        api_calls, backfilled, len(candidates),
    )
    return {"api_calls": api_calls, "backfilled": backfilled}


def enrich_with_omdb(
    conn: sqlite3.Connection,
    candidates: list[MergedCandidate],
    omdb_api_key: str,
    cache_ttl_hours: int = 24,
    *,
    db_path: str = "data/movietrace.db",
    request_date: str = "",
) -> dict:
    """Enrich candidates with IMDb rating/votes via OMDb, with 24h cache.

    Returns {"api_calls": int, "cache_hits": int, "enriched": int}.
    """
    client = OmdbDetailClient(omdb_api_key, db_path=db_path, request_date=request_date)
    api_calls = 0
    cache_hits = 0
    enriched = 0

    for c in candidates:
        if not c.imdb_id:
            continue

        formatted = format_imdb_id(c.imdb_id)
        if not formatted:
            continue

        # Check cache
        cached = _read_cache(conn, f"omdb:{formatted}", cache_ttl_hours)
        if cached:
            cache_hits += 1
            _apply_omdb_data(c, cached)
            enriched += 1
            continue

        # Call API
        try:
            data = client.get_by_imdb_id(formatted)
            api_calls += 1
        except Exception as exc:
            logger.warning("OMDb lookup failed for %s: %s", formatted, exc)
            continue

        if data:
            _write_cache(conn, f"omdb:{formatted}", data)
            _apply_omdb_data(c, data)
            enriched += 1

        time.sleep(1.0)  # polite between OMDb calls

    logger.info(
        "OMDb enrichment: api_calls=%d cache_hits=%d enriched=%d of %d",
        api_calls, cache_hits, enriched, len(candidates),
    )
    return {"api_calls": api_calls, "cache_hits": cache_hits, "enriched": enriched}


def enrich_with_tmdb_details(
    conn: sqlite3.Connection,
    candidates: list[MergedCandidate],
    bearer_token: str,
    cache_ttl_hours: int = 24,
    *,
    db_path: str = "data/movietrace.db",
    request_date: str = "",
) -> dict:
    """Fill release_date and language for candidates missing them (mainly FP-only).

    Returns {"api_calls": int, "cache_hits": int, "enriched": int}.
    """
    client = TmdbDetailClient(bearer_token, db_path=db_path, request_date=request_date)
    api_calls = 0
    cache_hits = 0
    enriched = 0

    for c in candidates:
        if not c.tmdb_id:
            continue
        # Skip if we already have good data from TMDb trending
        if c.tmdb_data and c.tmdb_data.get("release_date") and c.tmdb_data.get("original_language"):
            continue

        cache_key = f"tmdb:detail:{c.tmdb_id}:{c.media_type}"
        cached = _read_cache(conn, cache_key, cache_ttl_hours)
        if cached:
            cache_hits += 1
            _apply_tmdb_detail_data(c, cached)
            enriched += 1
            continue

        try:
            if c.media_type == "tv":
                data = client.get_tv_details(str(c.tmdb_id))
            else:
                data = client.get_movie_details(str(c.tmdb_id))
            api_calls += 1
        except Exception as exc:
            logger.warning("TMDb detail failed for %s (%s): %s", c.tmdb_id, c.media_type, exc)
            continue

        if data:
            _write_cache(conn, cache_key, data)
            _apply_tmdb_detail_data(c, data)
            enriched += 1

    logger.info(
        "TMDb detail enrichment: api_calls=%d cache_hits=%d enriched=%d of %d",
        api_calls, cache_hits, enriched, len(candidates),
    )
    return {"api_calls": api_calls, "cache_hits": cache_hits, "enriched": enriched}


def _read_cache(conn: sqlite3.Connection, key: str, ttl_hours: int) -> dict | None:
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=ttl_hours)).strftime("%Y-%m-%d %H:%M:%S")
    row = conn.execute(
        "select response_json from api_cache where source = 'omdb' and cache_key = ? and fetched_at >= ?",
        (key, cutoff),
    ).fetchone()
    if row:
        try:
            return json.loads(row[0])
        except (json.JSONDecodeError, TypeError):
            return None
    return None


def _write_cache(conn: sqlite3.Connection, key: str, data: dict) -> None:
    try:
        conn.execute(
            "insert or replace into api_cache (source, cache_key, response_json) values ('omdb', ?, ?)",
            (key, json.dumps(data, ensure_ascii=False)),
        )
        conn.commit()
    except Exception as exc:
        logger.warning("Failed to write OMDb cache for %s: %s", key, exc)


def _apply_omdb_data(c: MergedCandidate, data: dict) -> None:
    rating = data.get("imdbRating")
    votes = data.get("imdbVotes")
    if rating and rating != "N/A":
        try:
            c.imdb_rating = float(rating)
        except (ValueError, TypeError):
            c.imdb_rating = None
    else:
        c.imdb_rating = None
    if votes and votes != "N/A":
        try:
            c.imdb_votes = int(votes.replace(",", ""))
        except (ValueError, TypeError):
            c.imdb_votes = None
    else:
        c.imdb_votes = None


def _apply_tmdb_detail_data(c: MergedCandidate, data: dict) -> None:
    if not c.tmdb_data:
        c.tmdb_data = {}
    if not c.tmdb_data.get("release_date"):
        rd = data.get("release_date") or data.get("first_air_date")
        if rd:
            c.tmdb_data["release_date"] = rd
    if not c.tmdb_data.get("original_language"):
        lang = data.get("original_language")
        if lang:
            c.tmdb_data["original_language"] = lang
    if not c.tmdb_data.get("title"):
        title = data.get("title") or data.get("name")
        if title:
            c.tmdb_data["title"] = title
    if not c.tmdb_data.get("popularity"):
        pop = data.get("popularity")
        if pop:
            c.tmdb_data["popularity"] = float(pop)
    if not c.tmdb_data.get("vote_average"):
        va = data.get("vote_average")
        if va:
            c.tmdb_data["vote_average"] = float(va)
    if not c.tmdb_data.get("vote_count"):
        vc = data.get("vote_count")
        if vc:
            c.tmdb_data["vote_count"] = int(vc)
