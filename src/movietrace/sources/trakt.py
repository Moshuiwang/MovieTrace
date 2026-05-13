from __future__ import annotations

import json
from typing import Any

from movietrace.logging.api_usage import fingerprint_key
from movietrace.pipeline.entity_matching import BaselineItem, ExternalSearchResult
from movietrace.sources.http import get_json


class TraktSearchClient:
    def __init__(
        self,
        client_id: str,
        *,
        base_url: str = "https://api.trakt.tv",
        db_path: str = "",
        request_date: str = "",
    ):
        self.client_id = client_id
        self.base_url = base_url.rstrip("/")
        self._db_path = db_path
        self._request_date = request_date
        self._key_fp = fingerprint_key(client_id)

    def _log_ctx(self, endpoint: str, operation: str) -> dict | None:
        if not self._db_path or not self._request_date:
            return None
        return {
            "db_path": self._db_path,
            "service": "trakt",
            "endpoint": endpoint,
            "operation": operation,
            "request_date": self._request_date,
            "key_fingerprint": self._key_fp,
        }

    def search(
        self, query: str, baseline_item: BaselineItem
    ) -> list[ExternalSearchResult]:
        payload = get_json(
            f"{self.base_url}/search/movie,show",
            params={"query": query},
            headers={
                "trakt-api-key": self.client_id,
                "trakt-api-version": "2",
                "Content-Type": "application/json",
            },
            log_context=self._log_ctx("/search/movie,show", "trakt_search.search"),
        )
        if not isinstance(payload, list):
            return []
        return parse_trakt_search_results(payload)


def parse_trakt_search_results(payload: list[Any]) -> list[ExternalSearchResult]:
    parsed: list[ExternalSearchResult] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        item_type = item.get("type")
        if item_type not in {"movie", "show"}:
            continue
        entity = item.get(item_type)
        if not isinstance(entity, dict):
            continue
        title = entity.get("title")
        if not title:
            continue
        ids = entity.get("ids") if isinstance(entity.get("ids"), dict) else {}
        trakt_id = ids.get("trakt")
        parsed.append(
            ExternalSearchResult(
                source="trakt",
                external_id=str(trakt_id) if trakt_id is not None else None,
                title=str(title),
                media_type="tv" if item_type == "show" else "movie",
                year=_int_or_none(entity.get("year")),
                score=float(item.get("score") or 0.0),
                raw_payload=entity,
            )
        )
    return parsed


def _int_or_none(value: object) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


class TraktTrendingClient:
    """Trakt trending endpoint client (P1.7-C)."""

    def __init__(
        self,
        client_id: str,
        *,
        base_url: str = "https://api.trakt.tv",
        db_path: str = "",
        request_date: str = "",
    ):
        self.client_id = client_id
        self.base_url = base_url.rstrip("/")
        self._db_path = db_path
        self._request_date = request_date
        self._key_fp = fingerprint_key(client_id)

    def _log_ctx(self, endpoint: str, operation: str) -> dict | None:
        if not self._db_path or not self._request_date:
            return None
        return {
            "db_path": self._db_path,
            "service": "trakt",
            "endpoint": endpoint,
            "operation": operation,
            "request_date": self._request_date,
            "key_fingerprint": self._key_fp,
        }

    def _headers(self) -> dict[str, str]:
        return {
            "trakt-api-key": self.client_id,
            "trakt-api-version": "2",
            "Content-Type": "application/json",
        }

    def fetch_shows_trending(self, limit: int = 500) -> list[dict]:
        """GET /shows/trending?limit=N&extended=full — returns flattened items."""
        payload = get_json(
            f"{self.base_url}/shows/trending",
            params={"limit": str(limit), "extended": "full"},
            headers=self._headers(),
            log_context=self._log_ctx("/shows/trending", "trakt_trending.fetch_shows_trending"),
        )
        if not isinstance(payload, list):
            return []
        return [_flatten_trakt_trending_item(item, "show") for item in payload]

    def fetch_movies_trending(self, limit: int = 500) -> list[dict]:
        """GET /movies/trending?limit=N&extended=full — returns flattened items."""
        payload = get_json(
            f"{self.base_url}/movies/trending",
            params={"limit": str(limit), "extended": "full"},
            headers=self._headers(),
            log_context=self._log_ctx("/movies/trending", "trakt_trending.fetch_movies_trending"),
        )
        if not isinstance(payload, list):
            return []
        return [_flatten_trakt_trending_item(item, "movie") for item in payload]


def _flatten_trakt_trending_item(item: dict, media_type: str) -> dict:
    """Flatten Trakt trending nested structure into a flat dict."""
    entity = item.get(media_type) if isinstance(item.get(media_type), dict) else {}
    ids = entity.get("ids") if isinstance(entity.get("ids"), dict) else {}
    return {
        "watchers": int(item.get("watchers") or 0),
        "trakt_id": ids.get("trakt"),
        "tmdb_id": ids.get("tmdb"),
        "imdb_id": str(ids.get("imdb")) if ids.get("imdb") else None,
        "title": str(entity.get("title") or ""),
        "year": _int_or_none(entity.get("year")),
        "rating": float(entity.get("rating")) if entity.get("rating") is not None else None,
        "votes": int(entity.get("votes")) if entity.get("votes") is not None else None,
        "media_type": media_type,
        "raw_payload": item,
        # P1.8-E: structured fields
        "genres": entity.get("genres"),
        "trakt_status": entity.get("status"),
        "country": entity.get("country"),
        "network": entity.get("network"),
        "runtime": _int_or_none(entity.get("runtime")),
        "overview": entity.get("overview"),
        "first_aired": entity.get("first_aired"),
        "aired_episodes": _int_or_none(entity.get("aired_episodes")),
        "certification": entity.get("certification"),
        "updated_at": entity.get("updated_at"),
    }


def normalize_trakt_trending_row(item: dict, source_endpoint: str, snapshot_date: str) -> dict | None:
    """Normalize a flattened Trakt trending item into a trakt_trending row dict."""
    if not item.get("trakt_id"):
        return None
    def _or_none_json(obj: object) -> str | None:
        if obj is None:
            return None
        return json.dumps(obj, ensure_ascii=False)

    return {
        "trakt_id": int(item["trakt_id"]),
        "tmdb_id": int(item["tmdb_id"]) if item.get("tmdb_id") else None,
        "imdb_id": str(item["imdb_id"]) if item.get("imdb_id") else None,
        "media_type": item["media_type"],
        "title": item["title"],
        "year": item.get("year"),
        "watchers": int(item.get("watchers") or 0),
        "rating": float(item["rating"]) if item.get("rating") is not None else None,
        "votes": int(item["votes"]) if item.get("votes") is not None else None,
        "source_endpoint": source_endpoint,
        "snapshot_date": snapshot_date,
        "raw_payload_json": json.dumps(item.get("raw_payload", item), ensure_ascii=False),
        # P1.8-E: structured fields
        "genres_json": _or_none_json(item.get("genres")),
        "trakt_status": item.get("trakt_status"),
        "country": item.get("country"),
        "network": item.get("network"),
        "runtime": item.get("runtime"),
        "overview": item.get("overview"),
        "first_aired": item.get("first_aired"),
        "aired_episodes": item.get("aired_episodes"),
        "certification": item.get("certification"),
        "updated_at": item.get("updated_at"),
    }
