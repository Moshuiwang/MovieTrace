from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Protocol


class TmdbDetailGetter(Protocol):
    def get_tv_details(self, tmdb_tv_id: str) -> dict: ...

    def get_movie_details(self, tmdb_movie_id: str) -> dict: ...


class TmdbSeasonDetailGetter(Protocol):
    def get_tv_season_details(self, tmdb_tv_id: str | int, season_number: int) -> dict: ...


def detail_cache_key(tmdb_id: str | int, media_type: str) -> str:
    normalized_type = "tv" if media_type in ("tv", "show") else "movie"
    return f"tmdb:detail:{tmdb_id}:{normalized_type}"


def read_tmdb_detail_cache(
    conn: sqlite3.Connection,
    tmdb_id: str | int,
    media_type: str,
    *,
    ttl_hours: int = 24,
    required_keys: tuple[str, ...] = (),
) -> dict | None:
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=ttl_hours)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    row = conn.execute(
        """select response_json from api_cache
           where source = 'tmdb' and cache_key = ? and fetched_at >= ?""",
        (detail_cache_key(tmdb_id, media_type), cutoff),
    ).fetchone()
    if not row:
        return None
    try:
        data = json.loads(row[0])
    except (json.JSONDecodeError, TypeError):
        return None
    if required_keys and any(data.get(key) is None for key in required_keys):
        return None
    return data if isinstance(data, dict) else None


def write_tmdb_detail_cache(
    conn: sqlite3.Connection,
    tmdb_id: str | int,
    media_type: str,
    data: dict,
) -> None:
    conn.execute(
        """insert or replace into api_cache (source, cache_key, response_json)
           values ('tmdb', ?, ?)""",
        (detail_cache_key(tmdb_id, media_type), json.dumps(data, ensure_ascii=False)),
    )
    conn.commit()


def get_tmdb_detail_with_cache(
    conn: sqlite3.Connection,
    client: TmdbDetailGetter,
    tmdb_id: str | int,
    media_type: str,
    *,
    ttl_hours: int = 24,
    required_keys: tuple[str, ...] = (),
) -> tuple[dict | None, bool]:
    cached = read_tmdb_detail_cache(
        conn,
        tmdb_id,
        media_type,
        ttl_hours=ttl_hours,
        required_keys=required_keys,
    )
    if cached:
        return cached, True

    normalized_type = "tv" if media_type in ("tv", "show") else "movie"
    if normalized_type == "tv":
        data = client.get_tv_details(str(tmdb_id))
    else:
        data = client.get_movie_details(str(tmdb_id))
    if isinstance(data, dict) and data:
        write_tmdb_detail_cache(conn, tmdb_id, normalized_type, data)
        return data, False
    return None, False


def season_detail_cache_key(tv_id: str | int, season_n: int) -> str:
    """Generate cache key for TV season detail: tmdb:detail:{tv_id}:season:{season_n}"""
    return f"tmdb:detail:{tv_id}:season:{season_n}"


def read_tmdb_season_detail_cache(
    conn: sqlite3.Connection,
    tv_id: str | int,
    season_n: int,
    *,
    ttl_hours: int = 24,
) -> dict | None:
    """Read season detail from api_cache (24h TTL default)."""
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=ttl_hours)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    row = conn.execute(
        """select response_json from api_cache
           where source = 'tmdb' and cache_key = ? and fetched_at >= ?""",
        (season_detail_cache_key(tv_id, season_n), cutoff),
    ).fetchone()
    if not row:
        return None
    try:
        data = json.loads(row[0])
    except (json.JSONDecodeError, TypeError):
        return None
    return data if isinstance(data, dict) else None


def write_tmdb_season_detail_cache(
    conn: sqlite3.Connection,
    tv_id: str | int,
    season_n: int,
    data: dict,
) -> None:
    """Write season detail to api_cache."""
    conn.execute(
        """insert or replace into api_cache (source, cache_key, response_json)
           values ('tmdb', ?, ?)""",
        (season_detail_cache_key(tv_id, season_n), json.dumps(data, ensure_ascii=False)),
    )
    conn.commit()


def get_tmdb_season_detail_with_cache(
    conn: sqlite3.Connection,
    client: TmdbSeasonDetailGetter,
    tv_id: str | int,
    season_n: int,
    *,
    ttl_hours: int = 24,
) -> tuple[dict | None, bool]:
    """Get season detail with 24h cache. Returns (data, was_cached)."""
    cached = read_tmdb_season_detail_cache(conn, tv_id, season_n, ttl_hours=ttl_hours)
    if cached:
        return cached, True

    data = client.get_tv_season_details(tv_id, season_n)
    if isinstance(data, dict) and data:
        write_tmdb_season_detail_cache(conn, tv_id, season_n, data)
        return data, False
    return None, False
