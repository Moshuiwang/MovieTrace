from __future__ import annotations

from typing import Any

from movietrace.pipeline.entity_matching import BaselineItem, ExternalSearchResult
from movietrace.sources.http import get_json


class TraktSearchClient:
    def __init__(self, client_id: str, *, base_url: str = "https://api.trakt.tv"):
        self.client_id = client_id
        self.base_url = base_url.rstrip("/")

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
