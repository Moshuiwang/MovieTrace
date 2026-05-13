from __future__ import annotations

import base64
import json
import logging
import re
import time
from pathlib import Path

from movietrace.logging.api_usage import fingerprint_key
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
    "paramount-plus": "cmp_riMmDaNhomIc4J2dWGQPKbkZ",
}

# Country/region IDs for FP API
FP_COUNTRIES: dict[str, str] = {
    "world": "cnt_aP0RJTnt9XO4bVmoriU3Ih7q",
    "united-states": "cnt_iMUHNbZvnNHK5YdhgwtOoP4u",
    "nigeria": "cnt_CfX89vcTOtjqMu0ng6w2QIfD",
    "kenya": "cnt_phcns8OP1rtHnX6QwlEKhiqU",
}

COUNTRY_ID_TO_NAME: dict[str, str] = {v: k for k, v in FP_COUNTRIES.items()}
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
        # P1.8-E: raw IDs for traceability
        "country_id": country_id,
        "company_id": platform_company_id,
    }


class FlixPatrolClient:
    def __init__(
        self,
        api_key: str,
        timeout: int = 60,
        *,
        db_path: str = "",
        request_date: str = "",
    ):
        self._api_key = api_key
        self.timeout = timeout
        self._masked_key = api_key[:4] + "***" if len(api_key) > 4 else "***"
        self._db_path = db_path
        self._request_date = request_date
        self._key_fp = fingerprint_key(api_key)

    def _log_ctx(self, endpoint: str, operation: str) -> dict | None:
        if not self._db_path or not self._request_date:
            return None
        return {
            "db_path": self._db_path,
            "service": "flixpatrol",
            "endpoint": endpoint,
            "operation": operation,
            "request_date": self._request_date,
            "key_fingerprint": self._key_fp,
        }

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
        log_ctx = self._log_ctx("/top10s", f"flixpatrol.fetch_top10.{ct_str}")
        start = time.monotonic()
        try:
            payload = get_json(url, params=params, headers=headers, timeout=self.timeout, log_context=log_ctx)
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
                    payload = get_json(url, params=params, headers=headers, timeout=self.timeout, log_context=log_ctx)
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
        self,
        date_from: str | None = None,
        *,
        fetch_movies: bool = False,
        countries: list[str] | None = None,
        platforms: list[str] | None = None,
        sleep_seconds: float = 2.0,
    ) -> dict:
        """Fetch FP top 10 across countries × platforms × content types.

        Returns dict with keys: results, planned_calls, actual_calls,
        tv_calls, movie_calls, country_count, platform_count.
        """
        if countries is None:
            countries = list(FP_COUNTRIES.keys())
        if platforms is None:
            platforms = list(PLATFORM_COMPANY_IDS.keys())

        content_types = [(3, "tv_show")]  # TV always daily
        if fetch_movies:
            content_types.append((2, "movie"))

        planned = len(countries) * len(platforms) * len(content_types)
        country_count = len(countries)
        platform_count = len(platforms)
        tv_planned = len(countries) * len(platforms)  # type 3 only
        movie_planned = len(countries) * len(platforms) if fetch_movies else 0

        logger.info(
            "flixpatrol fetch_all: countries=%d platforms=%d types=%d planned=%d (tv=%d movie=%d)",
            country_count, platform_count, len(content_types), planned,
            tv_planned, movie_planned,
        )

        results: dict[str, list[dict]] = {}
        actual = 0
        tv_actual = 0
        movie_actual = 0

        total_combos = len(countries) * len(platforms) * len(content_types)
        combo_idx = 0
        for country_slug in countries:
            country_id = FP_COUNTRIES.get(country_slug)
            if not country_id:
                logger.warning("Unknown FP country slug: %s — skipping", country_slug)
                continue
            for platform_key in platforms:
                company_id = PLATFORM_COMPANY_IDS.get(platform_key)
                if not company_id:
                    logger.warning("Unknown FP platform: %s — skipping", platform_key)
                    continue
                for content_type, type_name in content_types:
                    key = f"{country_slug}/{platform_key}/{type_name}"
                    items = self.fetch_top10(
                        company=company_id,
                        country=country_id,
                        content_type=content_type,
                        date_from=date_from,
                    )
                    results[key] = items
                    actual += 1
                    if content_type == 3:
                        tv_actual += 1
                    else:
                        movie_actual += 1

                    combo_idx += 1
                    if combo_idx < total_combos:
                        time.sleep(sleep_seconds)

        monthly_low = planned * 30 + movie_planned * (4.35 - 4) if fetch_movies else planned * 30
        monthly_high = planned * 31 + (movie_planned * 5 if fetch_movies else 0)

        stats = {
            "results": results,
            "planned_calls": planned,
            "actual_calls": actual,
            "tv_calls": tv_actual,
            "movie_calls": movie_actual,
            "country_count": country_count,
            "platform_count": platform_count,
            "monthly_estimate_low": planned * 30 + (movie_planned * 4 if fetch_movies else 0),
            "monthly_estimate_high": planned * 31 + (movie_planned * 5 if fetch_movies else 0),
        }
        return stats


def _extract_http_status(error_msg: str) -> int | None:
    m = re.search(r"HTTP Error (\d{3})", error_msg)
    return int(m.group(1)) if m else None
