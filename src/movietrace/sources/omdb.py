from __future__ import annotations

from typing import Any

from movietrace.pipeline.entity_matching import BaselineItem, ExternalSearchResult
from movietrace.sources.http import get_json


class OmdbSearchClient:
    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://www.omdbapi.com/",
    ):
        self.api_key = api_key
        self.base_url = base_url

    def search(
        self, query: str, baseline_item: BaselineItem
    ) -> list[ExternalSearchResult]:
        params = {
            "apikey": self.api_key,
            "s": query,
        }
        if baseline_item.content_granularity == "season":
            params["type"] = "series"
        payload = get_json(self.base_url, params=params)
        if not isinstance(payload, dict):
            return []
        return parse_omdb_search_results(payload)


def parse_omdb_search_results(payload: dict[str, Any]) -> list[ExternalSearchResult]:
    if payload.get("Response") != "True":
        return []
    parsed: list[ExternalSearchResult] = []
    for item in payload.get("Search") or []:
        if not isinstance(item, dict):
            continue
        result = _result_from_omdb_item(item)
        if result is not None:
            parsed.append(result)
    return parsed


def parse_omdb_detail_result(payload: dict[str, Any]) -> ExternalSearchResult | None:
    if payload.get("Response") != "True":
        return None
    return _result_from_omdb_item(payload)


def _result_from_omdb_item(item: dict[str, Any]) -> ExternalSearchResult | None:
    title = item.get("Title")
    imdb_id = item.get("imdbID")
    if not title or not imdb_id:
        return None
    media_type = _media_type(item.get("Type"))
    return ExternalSearchResult(
        source="omdb",
        external_id=str(imdb_id),
        title=str(title),
        media_type=media_type,
        year=_year_from_omdb(item.get("Year")),
        score=_score_from_rating_votes(item),
        raw_payload=item,
    )


def _media_type(value: object) -> str | None:
    if value == "series":
        return "tv"
    if value == "movie":
        return "movie"
    if value == "episode":
        return "episode"
    return None


def _year_from_omdb(value: object) -> int | None:
    if not isinstance(value, str):
        return None
    digits = "".join(ch if ch.isdigit() else " " for ch in value).split()
    if not digits:
        return None
    try:
        return int(digits[0])
    except ValueError:
        return None


def _score_from_rating_votes(item: dict[str, Any]) -> float:
    rating = _float_or_zero(item.get("imdbRating"))
    votes = _votes_or_zero(item.get("imdbVotes"))
    return rating + min(votes / 100_000, 10.0)


def _float_or_zero(value: object) -> float:
    if not isinstance(value, str) or value == "N/A":
        return 0.0
    try:
        return float(value)
    except ValueError:
        return 0.0


def _votes_or_zero(value: object) -> int:
    if not isinstance(value, str) or value == "N/A":
        return 0
    try:
        return int(value.replace(",", ""))
    except ValueError:
        return 0


class OmdbDetailClient:
    """OMDb detail lookup by IMDb ID (P1.7-D)."""

    def __init__(self, api_key: str, *, base_url: str = "https://www.omdbapi.com/"):
        self.api_key = api_key
        self.base_url = base_url

    def get_by_imdb_id(self, imdb_id: str) -> dict | None:
        """GET ?i=<imdb_id>&apikey=... — returns {imdbRating, imdbVotes} or None."""
        payload = get_json(
            self.base_url,
            params={"i": imdb_id, "apikey": self.api_key},
        )
        if not isinstance(payload, dict) or payload.get("Response") != "True":
            return None
        return payload


def format_imdb_id(raw: str) -> str:
    """Normalize a raw IMDb ID to tt-prefixed 7-digit format.

    '1190634' → 'tt1190634', 'tt1190634' → 'tt1190634'.
    """
    cleaned = str(raw).strip()
    if cleaned.lower().startswith("tt"):
        digits = cleaned[2:]
    else:
        digits = cleaned
    digits = digits.zfill(7)
    return f"tt{digits}"
