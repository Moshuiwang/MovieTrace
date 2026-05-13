from __future__ import annotations

import json
from typing import Any

from movietrace.pipeline.entity_matching import BaselineItem, ExternalSearchResult
from movietrace.sources.http import get_json


class TmdbSearchClient:
    def __init__(
        self,
        bearer_token: str,
        *,
        base_url: str = "https://api.themoviedb.org/3",
    ):
        self.bearer_token = bearer_token
        self.base_url = base_url.rstrip("/")

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
        )
        if not isinstance(payload, dict):
            return []
        return parse_tmdb_search_results(payload)

    def search_tv(self, query: str) -> list[ExternalSearchResult]:
        """Search /search/tv — returns only TV results."""
        payload = get_json(
            f"{self.base_url}/search/tv",
            params={"query": query, "include_adult": "false", "language": "en-US"},
            headers={
                "Authorization": f"Bearer {self.bearer_token}",
                "Accept": "application/json",
            },
        )
        if not isinstance(payload, dict):
            return []
        return parse_tmdb_search_results(payload, default_media_type="tv")

    def search_movie(self, query: str) -> list[ExternalSearchResult]:
        """Search /search/movie — returns only movie results."""
        payload = get_json(
            f"{self.base_url}/search/movie",
            params={"query": query, "include_adult": "false", "language": "en-US"},
            headers={
                "Authorization": f"Bearer {self.bearer_token}",
                "Accept": "application/json",
            },
        )
        if not isinstance(payload, dict):
            return []
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
    ):
        self.bearer_token = bearer_token
        self.base_url = base_url.rstrip("/")

    def get_tv_details(self, tmdb_tv_id: str) -> dict:
        """GET /tv/{tv_id} — returns raw TMDb response dict."""
        payload = get_json(
            f"{self.base_url}/tv/{tmdb_tv_id}",
            params={"language": "en-US"},
            headers={
                "Authorization": f"Bearer {self.bearer_token}",
                "Accept": "application/json",
            },
        )
        if isinstance(payload, dict):
            return payload
        return {}

    def get_movie_details(self, tmdb_movie_id: str) -> dict:
        """GET /movie/{movie_id} — returns raw TMDb response dict."""
        payload = get_json(
            f"{self.base_url}/movie/{tmdb_movie_id}",
            params={"language": "en-US"},
            headers={
                "Authorization": f"Bearer {self.bearer_token}",
                "Accept": "application/json",
            },
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
    ):
        self.bearer_token = bearer_token
        self.base_url = base_url.rstrip("/")

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
        )
        if not isinstance(payload, dict):
            return []
        results = payload.get("results") or []
        for item in results:
            if isinstance(item, dict):
                item["media_type"] = "movie"
        return results


def normalize_tmdb_trending_row(item: dict, source_endpoint: str, source_page: int, snapshot_date: str) -> dict | None:
    """Normalize a raw TMDb trending/popular item into a tmdb_trending row dict."""
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
    }
