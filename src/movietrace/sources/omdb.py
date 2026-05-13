from __future__ import annotations

from typing import Any

from movietrace.logging.api_usage import fingerprint_key
from movietrace.pipeline.entity_matching import BaselineItem, ExternalSearchResult
from movietrace.sources.http import get_json


class OmdbSearchClient:
    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://www.omdbapi.com/",
        db_path: str = "",
        request_date: str = "",
    ):
        self.api_key = api_key
        self.base_url = base_url
        self._db_path = db_path
        self._request_date = request_date
        self._key_fp = fingerprint_key(api_key)

    def _log_ctx(self, endpoint: str, operation: str) -> dict | None:
        if not self._db_path or not self._request_date:
            return None
        return {
            "db_path": self._db_path,
            "service": "omdb",
            "endpoint": endpoint,
            "operation": operation,
            "request_date": self._request_date,
            "key_fingerprint": self._key_fp,
        }

    def search(
        self, query: str, baseline_item: BaselineItem
    ) -> list[ExternalSearchResult]:
        params = {
            "apikey": self.api_key,
            "s": query,
        }
        if baseline_item.content_granularity == "season":
            params["type"] = "series"
        payload = get_json(
            self.base_url,
            params=params,
            log_context=self._log_ctx("/?s", "omdb_search.search"),
        )
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

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://www.omdbapi.com/",
        db_path: str = "",
        request_date: str = "",
    ):
        self.api_key = api_key
        self.base_url = base_url
        self._db_path = db_path
        self._request_date = request_date
        self._key_fp = fingerprint_key(api_key)

    def _log_ctx(self, endpoint: str, operation: str) -> dict | None:
        if not self._db_path or not self._request_date:
            return None
        return {
            "db_path": self._db_path,
            "service": "omdb",
            "endpoint": endpoint,
            "operation": operation,
            "request_date": self._request_date,
            "key_fingerprint": self._key_fp,
        }

    def get_by_imdb_id(self, imdb_id: str) -> dict | None:
        """GET ?i=<imdb_id>&apikey=... — returns {imdbRating, imdbVotes} or None."""
        payload = get_json(
            self.base_url,
            params={"i": imdb_id, "apikey": self.api_key},
            log_context=self._log_ctx("/?i", "omdb_detail.get_by_imdb_id"),
        )
        if not isinstance(payload, dict) or payload.get("Response") != "True":
            # Check for quota error in response
            error_msg = payload.get("Error", "") if isinstance(payload, dict) else ""
            if "limit reached" in error_msg.lower():
                _log_omdb_quota_error(self._db_path, self._request_date, self._key_fp, error_msg)
            return None
        return payload


def _log_omdb_quota_error(
    db_path: str, request_date: str, key_fp: str, error_msg: str
) -> None:
    """Log OMDb quota error detected from response body."""
    if not db_path or not request_date:
        return
    try:
        from movietrace.logging.api_usage import log_api_call

        log_api_call(
            db_path=db_path,
            service="omdb",
            endpoint="/?i",
            operation="omdb_detail.get_by_imdb_id",
            request_date=request_date,
            status="http_error",
            http_status=401,
            quota_error=True,
            error_message=error_msg[:500],
            key_fingerprint=key_fp,
        )
    except Exception:
        pass


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
