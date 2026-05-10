from __future__ import annotations

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


def parse_tmdb_search_results(payload: dict[str, Any]) -> list[ExternalSearchResult]:
    parsed: list[ExternalSearchResult] = []
    for item in payload.get("results") or []:
        if not isinstance(item, dict):
            continue
        media_type = item.get("media_type")
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
