from __future__ import annotations

import base64
import json
import logging
import re
import time
from pathlib import Path

from movietrace.sources.http import get_json

logger = logging.getLogger("movietrace.sources.flixpatrol_api")

SECRETS_PATH = "/tmp/movietrace_phase0_secrets.json"
API_BASE_URL = "https://api.flixpatrol.com/v2"
UA = "MovieTraceBot/0.1"

PLATFORM_COMPANY_IDS: dict[str, str] = {
    "netflix": "cmp_IA6TdMqwf6kuyQvxo9bJ4nKX",
    "prime-video": "cmp_qypvowjqFhEIpCc0HlQ6VoYk",
    "disney-plus": "cmp_oGtsgdpOrjIu3XzTEnWPt87Y",
    "apple-tv-plus": "cmp_VvmYc7OphiUds0Hgjbz5MESn",
    "hbo-max": "cmp_6UhCvnTeRkgZUtcNGslX9bJL",
    "hulu": "cmp_9iwHIMYOCvD6zprSPoHgTJau",
}

US_COUNTRY_ID = "cnt_iMUHNbZvnNHK5YdhgwtOoP4u"

COUNTRY_ID_TO_NAME: dict[str, str] = {
    US_COUNTRY_ID: "united-states",
}
COMPANY_TO_PLATFORM: dict[str, str] = {v: k for k, v in PLATFORM_COMPANY_IDS.items()}
TYPE_INT_TO_STR: dict[int, str] = {2: "movie", 3: "tv_show"}


def load_api_key(secrets_path: str = SECRETS_PATH) -> str:
    try:
        data = json.loads(Path(secrets_path).read_text())
    except FileNotFoundError:
        raise RuntimeError(f"Secrets file not found: {secrets_path}")
    except json.JSONDecodeError:
        raise RuntimeError(f"Secrets file is not valid JSON: {secrets_path}")

    key = data.get("flixpatrol", {}).get("api_key")
    if not key:
        raise RuntimeError(
            "FlixPatrol API key not found in secrets file. "
            "Expected: secrets['flixpatrol']['api_key']"
        )
    return key


def unwrap_item(raw_item: dict) -> dict:
    inner = raw_item.get("data")
    if not isinstance(inner, dict):
        inner = {}

    movie_data = (inner.get("movie") or {}).get("data") or {}
    # "company" field holds platform info in compound doc format
    company_obj = inner.get("company") or inner.get("platform") or {}
    platform_data = company_obj.get("data") or {}
    country_data = (inner.get("country") or {}).get("data") or {}
    # "date" may be direct dict {type, from, to} in compound doc
    date_obj = inner.get("date") or {}
    snapshot_date = date_obj.get("from") if isinstance(date_obj, dict) else None
    # "type" may be direct int (compound doc) or nested {data: {type: 2}}
    type_obj = inner.get("type")
    if isinstance(type_obj, dict):
        content_type_int = type_obj.get("type")
    else:
        content_type_int = type_obj
    content_type_str = TYPE_INT_TO_STR.get(content_type_int)

    tmdb_id = movie_data.get("tmdbId")
    imdb_id_raw = movie_data.get("imdbId")
    if imdb_id_raw is not None:
        try:
            imdb_id = int(imdb_id_raw)
        except (ValueError, TypeError):
            imdb_id = None
    else:
        imdb_id = None

    country_id = country_data.get("id")
    country_name = (
        COUNTRY_ID_TO_NAME.get(country_id)
        or (country_data.get("name") or "unknown").lower().replace(" ", "-")
    )
    platform_company_id = platform_data.get("companyId") or platform_data.get("id")
    platform_name = COMPANY_TO_PLATFORM.get(
        platform_company_id, (platform_data.get("name") or "unknown").lower().replace(" ", "-")
    )

    return {
        "fp_id": inner.get("id") or raw_item.get("id"),
        "title": movie_data.get("title"),
        "content_type": content_type_str,
        "ranking": inner.get("ranking"),
        "ranking_last": inner.get("rankingLast"),
        "value": inner.get("value"),
        "days_total": inner.get("daysTotal"),
        "platform": platform_name,
        "country": country_name,
        "snapshot_date": snapshot_date,
        "tmdb_id": tmdb_id,
        "imdb_id": imdb_id,
        "updated_at": inner.get("updatedAt"),
    }


class FlixPatrolClient:
    def __init__(self, api_key: str, timeout: int = 60):
        self._api_key = api_key
        self.timeout = timeout
        self._masked_key = api_key[:4] + "***" if len(api_key) > 4 else "***"

    def _auth_header(self) -> str:
        credentials = base64.b64encode(f"{self._api_key}:".encode()).decode()
        return f"Basic {credentials}"

    def fetch_top10(
        self,
        company: str,
        country: str,
        content_type: int,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> list[dict]:
        params: dict[str, str] = {
            "company[eq]": company,
            "country[eq]": country,
            "type[eq]": str(content_type),
        }
        if date_from:
            params["date[from][gte]"] = date_from
            if date_to is None:
                date_to = date_from
        if date_to:
            params["date[from][lte]"] = date_to

        headers = {
            "Authorization": self._auth_header(),
            "Accept": "application/json",
            "User-Agent": UA,
        }
        url = f"{API_BASE_URL}/top10s"

        ct_str = TYPE_INT_TO_STR.get(content_type, str(content_type))
        start = time.monotonic()
        try:
            payload = get_json(url, params=params, headers=headers, timeout=self.timeout)
            elapsed = time.monotonic() - start
            items = payload.get("data") or []
            unwrapped = [unwrap_item(item) for item in items if isinstance(item, dict)]
            logger.info(
                "flixpatrol api: company=%s type=%s status=200 items=%d elapsed=%.1fs key=%s",
                company, ct_str, len(unwrapped), elapsed, self._masked_key,
            )
            return unwrapped
        except Exception as exc:
            elapsed = time.monotonic() - start
            status_code = _extract_http_status(str(exc))

            if status_code in (401, 403):
                logger.critical(
                    "flixpatrol api AUTH FAILED: company=%s status=%d elapsed=%.1fs",
                    company, status_code, elapsed,
                )
                raise RuntimeError(
                    f"FlixPatrol API authentication failed (HTTP {status_code}). "
                    f"Check API key."
                ) from exc

            if status_code == 429:
                logger.warning(
                    "flixpatrol api rate limited (429): company=%s — retrying in 5s",
                    company,
                )
                time.sleep(5)
                try:
                    payload = get_json(url, params=params, headers=headers, timeout=self.timeout)
                    retry_elapsed = time.monotonic() - start
                    items = payload.get("data") or []
                    unwrapped = [unwrap_item(item) for item in items if isinstance(item, dict)]
                    logger.info(
                        "flixpatrol api retry OK: company=%s items=%d total_elapsed=%.1fs",
                        company, len(unwrapped), retry_elapsed,
                    )
                    return unwrapped
                except Exception as retry_exc:
                    logger.warning(
                        "flixpatrol api retry also failed (429): company=%s — skipping",
                        company,
                    )
                    return []

            logger.error(
                "flixpatrol api failed: company=%s type=%s error=%s elapsed=%.1fs",
                company, ct_str, str(exc)[:200], elapsed,
            )
            return []

    def fetch_all_platforms(
        self, date_from: str | None = None
    ) -> dict[str, list[dict]]:
        results: dict[str, list[dict]] = {}

        platform_list = list(PLATFORM_COMPANY_IDS.items())
        for i, (platform_key, company_id) in enumerate(platform_list):
            for content_type, type_name in [(2, "movie"), (3, "tv_show")]:
                key = f"{platform_key}/{type_name}"
                items = self.fetch_top10(
                    company=company_id,
                    country=US_COUNTRY_ID,
                    content_type=content_type,
                    date_from=date_from,
                )
                results[key] = items
                # Wait between calls, skip after last call of last platform
                is_last = (i == len(platform_list) - 1 and content_type == 3)
                if not is_last:
                    time.sleep(1)
        return results


def _extract_http_status(error_msg: str) -> int | None:
    m = re.search(r"HTTP Error (\d{3})", error_msg)
    return int(m.group(1)) if m else None
