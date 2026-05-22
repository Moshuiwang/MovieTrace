from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any

from movietrace.pipeline.entity_matching import BaselineItem, ExternalSearchResult
from movietrace.logging.api_usage import fingerprint_key, log_api_call
from movietrace.sources.http import get_json


def _search_cache_key(media_type: str, query: str) -> str:
    """Generate cache key for TMDb search results.

    Format: tmdb:search:{media_type}:{query_norm}
    query_norm = query.strip().lower()
    """
    query_norm = query.strip().lower()
    return f"tmdb:search:{media_type}:{query_norm}"


def _read_search_cache(
    conn: sqlite3.Connection,
    cache_key: str,
    ttl_hours: int,
) -> dict | None:
    """Read TMDb search result from api_cache. Returns None on miss or expiry."""
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=ttl_hours)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    row = conn.execute(
        """select response_json from api_cache
           where source = 'tmdb' and cache_key = ? and fetched_at >= ?""",
        (cache_key, cutoff),
    ).fetchone()
    if not row:
        return None
    try:
        data = json.loads(row[0])
    except (json.JSONDecodeError, TypeError):
        return None
    return data if isinstance(data, dict) else None


def _write_search_cache(
    conn: sqlite3.Connection,
    cache_key: str,
    data: dict,
) -> None:
    """Write TMDb search result to api_cache (insert or replace)."""
    conn.execute(
        """insert or replace into api_cache (source, cache_key, response_json)
           values ('tmdb', ?, ?)""",
        (cache_key, json.dumps(data, ensure_ascii=False)),
    )
    conn.commit()


class TmdbSearchClient:
    def __init__(
        self,
        bearer_token: str,
        *,
        base_url: str = "https://api.themoviedb.org/3",
        db_path: str = "",
        request_date: str = "",
        conn: sqlite3.Connection | None = None,
    ):
        self.bearer_token = bearer_token
        self.base_url = base_url.rstrip("/")
        self._db_path = db_path
        self._request_date = request_date
        self._key_fp = fingerprint_key(bearer_token)
        self._conn = conn

    def _log_ctx(self, endpoint: str, operation: str) -> dict | None:
        if not self._db_path or not self._request_date:
            return None
        return {
            "db_path": self._db_path,
            "service": "tmdb",
            "endpoint": endpoint,
            "operation": operation,
            "request_date": self._request_date,
            "key_fingerprint": self._key_fp,
        }

    def _log_cache_hit(self, endpoint: str, operation: str) -> None:
        """Write cache_hit row to api_usage_log if db_path and request_date are set."""
        if not self._db_path or not self._request_date:
            return
        log_api_call(
            db_path=self._db_path,
            service="tmdb",
            endpoint=endpoint,
            operation=operation,
            request_date=self._request_date,
            status="cache_hit",
            cache_status="hit",
            key_fingerprint=self._key_fp,
        )

    def search(
        self, query: str, baseline_item: BaselineItem
    ) -> list[ExternalSearchResult]:
        payload = get_json(
            f"{self.base_url}/search/multi",
            params={"query": query, "include_adult": "false", "language": "en-US"},
            headers={
                "Authorization": f"Bearer {self.bearer_token}",
                "Accept": "application/json",
            },
            log_context=self._log_ctx("/search/multi", "tmdb_search.search"),
        )
        if not isinstance(payload, dict):
            return []
        return parse_tmdb_search_results(payload)

    def search_tv(self, query: str, cache_ttl_hours: int = 72) -> list[ExternalSearchResult]:
        """Search /search/tv — returns only TV results. Results cached for 72h by default."""
        cache_key = _search_cache_key("tv", query)

        if self._conn is not None:
            cached = _read_search_cache(self._conn, cache_key, cache_ttl_hours)
            if cached is not None:
                self._log_cache_hit("/search/tv", "tmdb_search.search_tv")
                return parse_tmdb_search_results(cached, default_media_type="tv")

        payload = get_json(
            f"{self.base_url}/search/tv",
            params={"query": query, "include_adult": "false", "language": "en-US"},
            headers={
                "Authorization": f"Bearer {self.bearer_token}",
                "Accept": "application/json",
            },
            log_context=self._log_ctx("/search/tv", "tmdb_search.search_tv"),
        )
        if not isinstance(payload, dict):
            return []
        if self._conn is not None:
            _write_search_cache(self._conn, cache_key, payload)
        return parse_tmdb_search_results(payload, default_media_type="tv")

    def search_movie(self, query: str, cache_ttl_hours: int = 72) -> list[ExternalSearchResult]:
        """Search /search/movie — returns only movie results. Results cached for 72h by default."""
        cache_key = _search_cache_key("movie", query)

        if self._conn is not None:
            cached = _read_search_cache(self._conn, cache_key, cache_ttl_hours)
            if cached is not None:
                self._log_cache_hit("/search/movie", "tmdb_search.search_movie")
                return parse_tmdb_search_results(cached, default_media_type="movie")

        payload = get_json(
            f"{self.base_url}/search/movie",
            params={"query": query, "include_adult": "false", "language": "en-US"},
            headers={
                "Authorization": f"Bearer {self.bearer_token}",
                "Accept": "application/json",
            },
            log_context=self._log_ctx("/search/movie", "tmdb_search.search_movie"),
        )
        if not isinstance(payload, dict):
            return []
        if self._conn is not None:
            _write_search_cache(self._conn, cache_key, payload)
        return parse_tmdb_search_results(payload, default_media_type="movie")


def parse_tmdb_search_results(
    payload: dict[str, Any], default_media_type: str | None = None
) -> list[ExternalSearchResult]:
    """Parse TMDb search results. default_media_type is used when items lack media_type
    (as happens with /search/tv and /search/movie endpoints)."""
    parsed: list[ExternalSearchResult] = []
    for item in payload.get("results") or []:
        if not isinstance(item, dict):
            continue
        media_type = item.get("media_type") or default_media_type
        if media_type not in {"movie", "tv"}:
            continue
        title = item.get("title") if media_type == "movie" else item.get("name")
        if not title:
            continue
        date_value = item.get("release_date")
        if media_type == "tv":
            date_value = item.get("first_air_date")
        parsed.append(
            ExternalSearchResult(
                source="tmdb",
                external_id=str(item.get("id")) if item.get("id") is not None else None,
                title=str(title),
                media_type=str(media_type),
                year=_year_from_date(date_value),
                score=float(item.get("popularity") or 0.0),
                raw_payload=item,
            )
        )
    return parsed


def _year_from_date(value: object) -> int | None:
    if not isinstance(value, str) or len(value) < 4:
        return None
    try:
        return int(value[:4])
    except ValueError:
        return None


class TmdbDetailClient:
    """TMDb detail endpoint client (GET /tv/{id}, /movie/{id})."""

    def __init__(
        self,
        bearer_token: str,
        *,
        base_url: str = "https://api.themoviedb.org/3",
        db_path: str = "",
        request_date: str = "",
    ):
        self.bearer_token = bearer_token
        self.base_url = base_url.rstrip("/")
        self._db_path = db_path
        self._request_date = request_date
        self._key_fp = fingerprint_key(bearer_token)

    def _log_ctx(self, endpoint: str, operation: str) -> dict | None:
        if not self._db_path or not self._request_date:
            return None
        return {
            "db_path": self._db_path,
            "service": "tmdb",
            "endpoint": endpoint,
            "operation": operation,
            "request_date": self._request_date,
            "key_fingerprint": self._key_fp,
        }

    def get_tv_details(self, tmdb_tv_id: str, language: str = "en-US") -> dict:
        """GET /tv/{tv_id} — returns raw TMDb response dict."""
        payload = get_json(
            f"{self.base_url}/tv/{tmdb_tv_id}",
            params={"language": language},
            headers={
                "Authorization": f"Bearer {self.bearer_token}",
                "Accept": "application/json",
            },
            log_context=self._log_ctx(f"/tv/{tmdb_tv_id}", "tmdb_detail.get_tv_details"),
        )
        if isinstance(payload, dict):
            return payload
        return {}

    def get_movie_details(self, tmdb_movie_id: str, language: str = "en-US") -> dict:
        """GET /movie/{movie_id} — returns raw TMDb response dict."""
        payload = get_json(
            f"{self.base_url}/movie/{tmdb_movie_id}",
            params={"language": language},
            headers={
                "Authorization": f"Bearer {self.bearer_token}",
                "Accept": "application/json",
            },
            log_context=self._log_ctx(f"/movie/{tmdb_movie_id}", "tmdb_detail.get_movie_details"),
        )
        if isinstance(payload, dict):
            return payload
        return {}

    def get_tv_external_ids(self, tmdb_tv_id: int) -> dict:
        """GET /tv/{id}/external_ids — returns {imdb_id, tvdb_id, ...} (P1.8-F/G)."""
        payload = get_json(
            f"{self.base_url}/tv/{tmdb_tv_id}/external_ids",
            headers={
                "Authorization": f"Bearer {self.bearer_token}",
                "Accept": "application/json",
            },
            log_context=self._log_ctx(f"/tv/{tmdb_tv_id}/external_ids", "tmdb_detail.get_tv_external_ids"),
        )
        if isinstance(payload, dict):
            return payload
        return {}

    def get_movie_external_ids(self, tmdb_movie_id: int) -> dict:
        """GET /movie/{id}/external_ids — returns {imdb_id, ...} (P1.8-F/G)."""
        payload = get_json(
            f"{self.base_url}/movie/{tmdb_movie_id}/external_ids",
            headers={
                "Authorization": f"Bearer {self.bearer_token}",
                "Accept": "application/json",
            },
            log_context=self._log_ctx(f"/movie/{tmdb_movie_id}/external_ids", "tmdb_detail.get_movie_external_ids"),
        )
        if isinstance(payload, dict):
            return payload
        return {}

    def fetch_imdb_id(self, tmdb_id: int, media_type: str) -> str | None:
        """Get IMDb ID for a TMDb ID via external_ids endpoint."""
        if media_type == "tv":
            result = self.get_tv_external_ids(tmdb_id)
        else:
            result = self.get_movie_external_ids(tmdb_id)
        imdb = result.get("imdb_id")
        return str(imdb) if imdb else None

    def get_tv_season_details(self, tmdb_tv_id: str | int, season_number: int) -> dict:
        """GET /tv/{id}/season/{n} — returns season details dict (episode_count, episodes[], etc.)."""
        payload = get_json(
            f"{self.base_url}/tv/{tmdb_tv_id}/season/{season_number}",
            params={"language": "en-US"},
            headers={
                "Authorization": f"Bearer {self.bearer_token}",
                "Accept": "application/json",
            },
            log_context=self._log_ctx(f"/tv/{tmdb_tv_id}/season/{season_number}", "tmdb_detail.get_tv_season_details"),
        )
        if isinstance(payload, dict):
            return payload
        return {}


class TmdbTrendingClient:
    """TMDb trending / popular endpoint client (P1.7-B)."""

    def __init__(
        self,
        bearer_token: str,
        *,
        base_url: str = "https://api.themoviedb.org/3",
        db_path: str = "",
        request_date: str = "",
    ):
        self.bearer_token = bearer_token
        self.base_url = base_url.rstrip("/")
        self._db_path = db_path
        self._request_date = request_date
        self._key_fp = fingerprint_key(bearer_token)

    def _log_ctx(self, endpoint: str, operation: str) -> dict | None:
        if not self._db_path or not self._request_date:
            return None
        return {
            "db_path": self._db_path,
            "service": "tmdb",
            "endpoint": endpoint,
            "operation": operation,
            "request_date": self._request_date,
            "key_fingerprint": self._key_fp,
        }

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.bearer_token}",
            "Accept": "application/json",
        }

    def fetch_trending_all_day(self, page: int = 1) -> list[dict]:
        """GET /trending/all/day?page=N&language=en-US"""
        payload = get_json(
            f"{self.base_url}/trending/all/day",
            params={"page": str(page), "language": "en-US"},
            headers=self._headers(),
            log_context=self._log_ctx("/trending/all/day", "tmdb_trending.fetch_trending_all_day"),
        )
        if not isinstance(payload, dict):
            return []
        return payload.get("results") or []

    def fetch_tv_popular(self, page: int = 1) -> list[dict]:
        """GET /tv/popular?page=N&language=en-US"""
        payload = get_json(
            f"{self.base_url}/tv/popular",
            params={"page": str(page), "language": "en-US"},
            headers=self._headers(),
            log_context=self._log_ctx("/tv/popular", "tmdb_trending.fetch_tv_popular"),
        )
        if not isinstance(payload, dict):
            return []
        results = payload.get("results") or []
        for item in results:
            if isinstance(item, dict):
                item["media_type"] = "tv"
        return results

    def fetch_movie_popular(self, page: int = 1) -> list[dict]:
        """GET /movie/popular?page=N&language=en-US"""
        payload = get_json(
            f"{self.base_url}/movie/popular",
            params={"page": str(page), "language": "en-US"},
            headers=self._headers(),
            log_context=self._log_ctx("/movie/popular", "tmdb_trending.fetch_movie_popular"),
        )
        if not isinstance(payload, dict):
            return []
        results = payload.get("results") or []
        for item in results:
            if isinstance(item, dict):
                item["media_type"] = "movie"
        return results


def normalize_tmdb_trending_row(item: dict, source_endpoint: str, source_page: int, snapshot_date: str) -> dict | None:
    """Normalize a raw TMDb trending/popular item into a tmdb_trending row dict (P1.8-C)."""
    tmdb_id = item.get("id")
    if tmdb_id is None:
        return None
    media_type = item.get("media_type", "movie")
    if media_type not in ("movie", "tv"):
        return None
    title = item.get("title") if media_type == "movie" else item.get("name")
    if not title:
        return None
    original_title = item.get("original_title") if media_type == "movie" else item.get("original_name")
    release_date = item.get("release_date") if media_type == "movie" else item.get("first_air_date")

    def _or_none_json(obj: object) -> str | None:
        if obj is None:
            return None
        return json.dumps(obj, ensure_ascii=False)

    return {
        "tmdb_id": int(tmdb_id),
        "media_type": media_type,
        "title": str(title),
        "original_title": str(original_title) if original_title else None,
        "release_date": str(release_date) if release_date else None,
        "original_language": str(item.get("original_language")) if item.get("original_language") else None,
        "popularity": float(item.get("popularity") or 0.0),
        "vote_average": float(item.get("vote_average")) if item.get("vote_average") is not None else None,
        "vote_count": int(item.get("vote_count")) if item.get("vote_count") is not None else None,
        "source_endpoint": source_endpoint,
        "source_page": source_page,
        "snapshot_date": snapshot_date,
        "raw_payload_json": json.dumps(item, ensure_ascii=False),
        # P1.8-C: new structured fields from trending/popular payload
        "adult": 1 if item.get("adult") else 0,
        "softcore": 1 if item.get("softcore") else 0,
        "backdrop_path": str(item["backdrop_path"]) if item.get("backdrop_path") else None,
        "poster_path": str(item["poster_path"]) if item.get("poster_path") else None,
        "overview": str(item["overview"]) if item.get("overview") else None,
        "genre_ids_json": _or_none_json(item.get("genre_ids")),
        "origin_country_json": _or_none_json(item.get("origin_country")),
        "first_air_date": str(item["first_air_date"]) if media_type == "tv" and item.get("first_air_date") else None,
        "movie_release_date": str(item["release_date"]) if media_type == "movie" and item.get("release_date") else None,
        "original_name": str(item["original_name"]) if item.get("original_name") else None,
    }
