from __future__ import annotations

import json
import logging
import sqlite3
import time
from datetime import datetime, timedelta, timezone

from movietrace.pipeline.multi_source_merge import MergedCandidate
from movietrace.pipeline.tmdb_detail_cache import (
    get_tmdb_detail_with_cache,
    read_tmdb_detail_cache,
    write_tmdb_detail_cache,
)
from movietrace.sources.http import FatalApiError
from movietrace.sources.omdb import OmdbDetailClient, format_imdb_id
from movietrace.sources.tmdb import TmdbDetailClient
from movietrace.logging.api_usage import fingerprint_key

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
    omdb_api_keys: list[str],
    cache_ttl_hours: int = 24,
    *,
    db_path: str = "data/movietrace.db",
    request_date: str = "",
) -> dict:
    """Enrich candidates with IMDb rating/votes via OMDb, with 24h cache.

    Supports multiple API keys: when a key returns 401/403, it is marked dead
    and the next key is tried for the current candidate. When all keys are
    exhausted, the circuit breaker stops all further OMDb requests.

    Returns {"api_calls": int, "cache_hits": int, "enriched": int,
             "keys_used": int, "keys_exhausted": int}.
    """
    if not omdb_api_keys:
        return {"api_calls": 0, "cache_hits": 0, "enriched": 0, "keys_used": 0, "keys_exhausted": 0}

    active_keys = list(omdb_api_keys)
    dead_keys: set[str] = set()
    tried_keys: set[str] = set()
    api_calls = 0
    cache_hits = 0
    enriched = 0

    for c in candidates:
        if not active_keys:
            logger.warning(
                "OMDb circuit breaker: all %d keys exhausted (%d calls made) — stopping",
                len(dead_keys), api_calls,
            )
            break

        if not c.imdb_id:
            continue

        formatted = format_imdb_id(c.imdb_id)
        if not formatted:
            continue

        # Check cache (valid regardless of which key fetched it)
        cached = _read_cache(conn, f"omdb:{formatted}", cache_ttl_hours, source="omdb")
        if cached:
            cache_hits += 1
            _apply_omdb_data(c, cached)
            enriched += 1
            continue

        # Try each active key for this candidate
        enriched_for_candidate = False
        for key in active_keys:
            tried_keys.add(key)
            client = OmdbDetailClient(key, db_path=db_path, request_date=request_date)
            try:
                data = client.get_by_imdb_id(formatted)
                api_calls += 1
                enriched_for_candidate = True
                break
            except FatalApiError as exc:
                api_calls += 1
                dead_keys.add(key)
                logger.warning(
                    "OMDb key %s HTTP %s — marked dead, trying next key",
                    fingerprint_key(key), exc.status_code,
                )
                continue
            except Exception as exc:
                api_calls += 1
                logger.warning("OMDb lookup failed for %s: %s", formatted, exc)
                break  # non-fatal error, don't retry with other keys

        # Remove dead keys from active list
        active_keys = [k for k in active_keys if k not in dead_keys]

        if enriched_for_candidate and data:
            _write_cache(conn, f"omdb:{formatted}", data, source="omdb")
            _apply_omdb_data(c, data)
            enriched += 1

        time.sleep(1.0)  # polite between OMDb calls

    conn.commit()
    logger.info(
        "OMDb enrichment: api_calls=%d cache_hits=%d enriched=%d of %d keys_used=%d keys_exhausted=%d",
        api_calls, cache_hits, enriched, len(candidates),
        len(tried_keys), len(dead_keys),
    )
    return {
        "api_calls": api_calls,
        "cache_hits": cache_hits,
        "enriched": enriched,
        "keys_used": len(tried_keys),
        "keys_exhausted": len(dead_keys),
    }


def _fetch_zh_detail_with_cache(
    conn: sqlite3.Connection,
    client: TmdbDetailClient,
    tmdb_id: str | int,
    media_type: str,
    *,
    ttl_hours: int = 24,
) -> tuple[dict | None, bool]:
    """Fetch zh-CN TMDb detail, caching under a :zh-CN key."""
    normalized_type = "tv" if media_type in ("tv", "show") else "movie"
    cache_key = f"tmdb:detail:{tmdb_id}:{normalized_type}:zh-CN"
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=ttl_hours)).strftime("%Y-%m-%d %H:%M:%S")
    row = conn.execute(
        "select response_json from api_cache where source = 'tmdb' and cache_key = ? and fetched_at >= ?",
        (cache_key, cutoff),
    ).fetchone()
    if row:
        try:
            return json.loads(row[0]), True
        except (json.JSONDecodeError, TypeError):
            pass
    if normalized_type == "tv":
        data = client.get_tv_details(str(tmdb_id), language="zh-CN")
    else:
        data = client.get_movie_details(str(tmdb_id), language="zh-CN")
    if isinstance(data, dict) and data:
        conn.execute(
            "insert or replace into api_cache (source, cache_key, response_json) values (?, ?, ?)",
            ("tmdb", cache_key, json.dumps(data, ensure_ascii=False)),
        )
        return data, False
    return None, False


def _update_canonical_zh_fields(
    conn: sqlite3.Connection,
    tmdb_id: str | int,
    media_type: str,
    title_zh: str | None,
    overview_zh: str | None,
    genres_json: str | None,
    networks_json: str | None,
) -> bool:
    """Update canonical_items zh-CN fields via external_ids lookup. Returns True if found."""
    normalized_type = "tv" if media_type in ("tv", "show") else "movie"
    ext_id = f"{normalized_type}:{tmdb_id}"
    row = conn.execute(
        "select canonical_item_id from external_ids where source = 'tmdb' and external_id = ?",
        (ext_id,),
    ).fetchone()
    if not row:
        return False
    conn.execute(
        """update canonical_items
           set title_zh = ?, overview_zh = ?, genres_json = ?, networks_json = ?
           where id = ?""",
        (title_zh or None, overview_zh or None, genres_json, networks_json, row[0]),
    )
    return True


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
        # P1.9-hotfix-B: TV candidates also need last_air_date (not in trending payload)
        if c.tmdb_data and c.tmdb_data.get("release_date") and c.tmdb_data.get("original_language"):
            if c.media_type != "tv" or c.tmdb_data.get("last_air_date"):
                continue

        try:
            data, cache_hit = get_tmdb_detail_with_cache(
                conn,
                client,
                c.tmdb_id,
                c.media_type,
                ttl_hours=cache_ttl_hours,
            )
            if cache_hit:
                cache_hits += 1
            else:
                api_calls += 1
        except Exception as exc:
            logger.warning("TMDb detail failed for %s (%s): %s", c.tmdb_id, c.media_type, exc)
            continue

        if data:
            _apply_tmdb_detail_data(c, data)
            enriched += 1
            genres = data.get("genres")
            genres_json = json.dumps(genres, ensure_ascii=False) if isinstance(genres, list) else None
            networks = data.get("networks") if c.media_type in ("tv", "show") else None
            networks_json = json.dumps(networks, ensure_ascii=False) if isinstance(networks, list) else None
            try:
                zh_data, _ = _fetch_zh_detail_with_cache(
                    conn, client, c.tmdb_id, c.media_type, ttl_hours=cache_ttl_hours
                )
                title_zh = None
                overview_zh = None
                if zh_data:
                    raw_title = zh_data.get("name") or zh_data.get("title")
                    raw_overview = zh_data.get("overview")
                    title_zh = str(raw_title).strip() if raw_title else None
                    overview_zh = str(raw_overview).strip() if raw_overview else None
                _update_canonical_zh_fields(
                    conn, c.tmdb_id, c.media_type,
                    title_zh, overview_zh, genres_json, networks_json,
                )
            except Exception as exc:
                logger.warning("zh-CN enrichment failed for %s (%s): %s", c.tmdb_id, c.media_type, exc)

    conn.commit()
    logger.info(
        "TMDb detail enrichment: api_calls=%d cache_hits=%d enriched=%d of %d",
        api_calls, cache_hits, enriched, len(candidates),
    )
    return {"api_calls": api_calls, "cache_hits": cache_hits, "enriched": enriched}


def _read_cache(conn: sqlite3.Connection, key: str, ttl_hours: int, source: str = "tmdb") -> dict | None:
    if source == "tmdb" and key.startswith("tmdb:detail:"):
        parts = key.split(":")
        if len(parts) == 4:
            return read_tmdb_detail_cache(conn, parts[2], parts[3], ttl_hours=ttl_hours)
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=ttl_hours)).strftime("%Y-%m-%d %H:%M:%S")
    row = conn.execute(
        "select response_json from api_cache where source = ? and cache_key = ? and fetched_at >= ?",
        (source, key, cutoff),
    ).fetchone()
    if row:
        try:
            return json.loads(row[0])
        except (json.JSONDecodeError, TypeError):
            return None
    return None


def _write_cache(conn: sqlite3.Connection, key: str, data: dict, source: str = "tmdb") -> None:
    if source == "tmdb" and key.startswith("tmdb:detail:"):
        parts = key.split(":")
        if len(parts) == 4:
            write_tmdb_detail_cache(conn, parts[2], parts[3], data)
            return
    try:
        conn.execute(
            "insert or replace into api_cache (source, cache_key, response_json) values (?, ?, ?)",
            (source, key, json.dumps(data, ensure_ascii=False)),
        )
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
    # P1.9-hotfix-B: TV freshness fields from detail API
    if not c.tmdb_data.get("last_air_date"):
        lad = data.get("last_air_date")
        if lad:
            c.tmdb_data["last_air_date"] = str(lad)
    if not c.tmdb_data.get("last_episode_air_date"):
        lea = data.get("last_episode_to_air")
        if isinstance(lea, dict):
            c.tmdb_data["last_episode_air_date"] = str(lea.get("air_date", "")) if lea.get("air_date") else None
            c.tmdb_data["last_episode_to_air"] = lea
    if not c.tmdb_data.get("first_air_date"):
        fad = data.get("first_air_date")
        if fad:
            c.tmdb_data["first_air_date"] = str(fad)
    if not c.tmdb_data.get("movie_release_date") and data.get("release_date"):
        c.tmdb_data["movie_release_date"] = str(data["release_date"])
    if not c.tmdb_data.get("seasons") and isinstance(data.get("seasons"), list):
        c.tmdb_data["seasons"] = data["seasons"]
