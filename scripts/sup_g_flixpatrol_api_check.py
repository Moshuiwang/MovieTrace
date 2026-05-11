#!/usr/bin/env python3
"""SUP-G: FlixPatrol Paid API ($9.99/mo) connectivity, platform coverage, field completeness verification.

Usage:
    PYTHONPATH=src python scripts/sup_g_flixpatrol_api_check.py --dry-run
    PYTHONPATH=src python scripts/sup_g_flixpatrol_api_check.py > /tmp/sup_g_result.json
"""

import base64
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

SECRETS_PATH = "/tmp/movietrace_phase0_secrets.json"
RESPONSES_DIR = "data/sup_g_api_responses"
API_BASE = "https://api.flixpatrol.com/v2"

# Platform configurations for the 6 target services
ENDPOINTS = [
    {
        "platform": "netflix",
        "region": "united-states",
        "company": "cmp_IA6TdMqwf6kuyQvxo9bJ4nKX",
        "country": "cnt_iMUHNbZvnNHK5YdhgwtOoP4u",
        "content_type": 2,  # Movies
    },
    {
        "platform": "prime-video",
        "region": "united-states",
        "company": "cmp_qypvowjqFhEIpCc0HlQ6VoYk",
        "country": "cnt_iMUHNbZvnNHK5YdhgwtOoP4u",
        "content_type": 2,
    },
    {
        "platform": "disney-plus",
        "region": "united-states",
        "company": "cmp_oGtsgdpOrjIu3XzTEnWPt87Y",
        "country": "cnt_iMUHNbZvnNHK5YdhgwtOoP4u",
        "content_type": 2,
    },
    {
        "platform": "apple-tv-plus",
        "region": "united-states",
        "company": "cmp_VvmYc7OphiUds0Hgjbz5MESn",
        "country": "cnt_iMUHNbZvnNHK5YdhgwtOoP4u",
        "content_type": 2,
    },
    {
        "platform": "hbo-max",
        "region": "united-states",
        "company": "cmp_6UhCvnTeRkgZUtcNGslX9bJL",
        "country": "cnt_iMUHNbZvnNHK5YdhgwtOoP4u",
        "content_type": 2,
    },
    {
        "platform": "hulu",
        "region": "united-states",
        "company": "cmp_9iwHIMYOCvD6zprSPoHgTJau",
        "country": "cnt_iMUHNbZvnNHK5YdhgwtOoP4u",
        "content_type": 2,
    },
]

# Fields required for P1-C hot_score scoring
REQUIRED_FIELDS = {
    "movie": "title (resolved via titles endpoint)",
    "type": "content_type (2=movie, 3=tv show)",
    "ranking": "ranking (chart position 1-10)",
    "daysTotal": "days_in_top10 (persistence signal)",
    "company": "platform identifier",
    "country": "region identifier",
    "date": "snapshot_date",
}


def load_api_key() -> tuple[str | None, str | None, str | None]:
    """Load FlixPatrol API key from secrets file.

    Returns (api_key, error_message, key_masked).
    """
    if not os.path.exists(SECRETS_PATH):
        return None, f"Secrets file not found: {SECRETS_PATH}", None
    try:
        with open(SECRETS_PATH) as f:
            secrets = json.load(f)
    except json.JSONDecodeError as e:
        return None, f"Failed to parse secrets file: {e}", None

    fp = secrets.get("flixpatrol", {})
    api_key = fp.get("api_key")
    if not api_key:
        return None, "Missing 'flixpatrol.api_key' in secrets file", None

    # Mask: show first 4 and last 4
    if len(api_key) > 8:
        masked = api_key[:4] + "*" * (len(api_key) - 8) + api_key[-4:]
    else:
        masked = api_key[:2] + "*" * (len(api_key) - 2)
    return api_key, None, masked


def build_auth_header(api_key: str) -> str:
    """Build HTTP Basic Auth header value with API key as username, empty password."""
    credentials = base64.b64encode(f"{api_key}:".encode()).decode()
    return f"Basic {credentials}"


def call_endpoint(
    api_key: str, platform: str, company: str, country: str, content_type: int
) -> dict:
    """Call FlixPatrol top10s endpoint for a single platform/country/type combination.

    Returns result dict with status, timing, item count, fields, and errors.
    """
    params = {
        "company[eq]": company,
        "country[eq]": country,
        "date[type][eq]": "1",  # Day
        "type[eq]": str(content_type),
    }
    url = f"{API_BASE}/top10s?{urllib.parse.urlencode(params)}"

    result = {
        "platform": platform,
        "region": "united-states",
        "url": url,
        "status_code": None,
        "response_time_ms": None,
        "item_count": 0,
        "fields_present": [],
        "fields_missing_vs_required": [],
        "saved_to": None,
        "error": None,
    }

    req = urllib.request.Request(url)
    req.add_header("Authorization", build_auth_header(api_key))
    req.add_header("User-Agent", "MovieTraceBot/0.1")

    start = time.monotonic()
    try:
        resp = urllib.request.urlopen(req, timeout=60)
        elapsed_ms = round((time.monotonic() - start) * 1000)
        result["response_time_ms"] = elapsed_ms
        result["status_code"] = resp.status

        body = resp.read().decode("utf-8")
        data = json.loads(body)

        # Save raw response
        safe_name = f"{platform}_{result['region']}.json"
        os.makedirs(RESPONSES_DIR, exist_ok=True)
        save_path = os.path.join(RESPONSES_DIR, safe_name)
        with open(save_path, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        result["saved_to"] = save_path

        # Determine item list — API may wrap in 'data' or return array directly
        items = _extract_items(data)
        result["item_count"] = len(items)

        # Collect all field names from items (top-level + nested detection)
        all_fields: set[str] = set()
        has_tmdb_id = False
        for item in items:
            all_fields.update(item.keys())
            # Detect tmdbId inside nested movie object
            if "movie" in item and isinstance(item["movie"], dict):
                movie_data = item["movie"].get("data", {})
                if isinstance(movie_data, dict) and "tmdbId" in movie_data:
                    has_tmdb_id = True
        result["fields_present"] = sorted(all_fields)
        if has_tmdb_id:
            result["fields_present"].append("movie.data.tmdbId")

        # Check required fields
        missing = [f for f in REQUIRED_FIELDS if f not in all_fields]
        # tmdbId counts as resolving the "movie" requirement for title/TMDb linkage
        if has_tmdb_id and "movie" in missing:
            missing.remove("movie")
            if "movie.data.tmdbId" not in result["fields_present"]:
                result["fields_present"].append("movie.data.tmdbId")
        result["fields_missing_vs_required"] = missing

    except urllib.error.HTTPError as e:
        elapsed_ms = round((time.monotonic() - start) * 1000)
        result["response_time_ms"] = elapsed_ms
        result["status_code"] = e.code
        result["error"] = _read_error_body(e)
    except urllib.error.URLError as e:
        elapsed_ms = round((time.monotonic() - start) * 1000)
        result["response_time_ms"] = elapsed_ms
        result["error"] = f"Network/URL error: {e.reason}"
    except Exception as e:
        elapsed_ms = round((time.monotonic() - start) * 1000)
        result["response_time_ms"] = elapsed_ms
        result["error"] = f"Unexpected error: {e}"

    return result


def _extract_items(data: dict | list) -> list[dict]:
    """Extract item list from API response, unwrapping compound document format.

    FlixPatrol v2 API uses compound documents: each array element is
    {type, data: {actual_fields...}, legacy}.  We unwrap to the inner data dict.
    """
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        for key in ("data", "items", "results", "top10s", "records"):
            if key in data and isinstance(data[key], list):
                items = data[key]
                break
        else:
            return []
    else:
        return []

    unwrapped: list[dict] = []
    for item in items:
        if isinstance(item, dict) and "data" in item and isinstance(item["data"], dict):
            unwrapped.append(item["data"])
        else:
            unwrapped.append(item)
    return unwrapped


def _read_error_body(e: urllib.error.HTTPError) -> str:
    """Safely read error response body."""
    try:
        body = e.read().decode("utf-8")
        return f"HTTP {e.code}: {body[:500]}"
    except Exception:
        return f"HTTP {e.code}"


def mask_key_in_text(text: str, api_key: str) -> str:
    """Replace the real API key with a masked version in text output."""
    if len(api_key) > 8:
        masked = api_key[:4] + "*" * (len(api_key) - 8) + api_key[-4:]
    else:
        masked = api_key[:2] + "*" * (len(api_key) - 2)
    return text.replace(api_key, masked)


def dry_run() -> None:
    """Validate secrets loading without making real HTTP requests."""
    api_key, error, masked = load_api_key()
    if error:
        print(f"DRY-RUN FAILED: {error}", file=sys.stderr)
        sys.exit(1)

    print("--- DRY RUN: secrets loaded successfully ---", file=sys.stderr)
    print(f"  Key source: {SECRETS_PATH}", file=sys.stderr)
    print(f"  Key masked: {masked}", file=sys.stderr)
    print(f"  Endpoints to call: {len(ENDPOINTS)}", file=sys.stderr)
    for ep in ENDPOINTS:
        params = {
            "company[eq]": ep["company"],
            "country[eq]": ep["country"],
            "date[type]": "1",
            "type[eq]": str(ep["content_type"]),
        }
        url = f"{API_BASE}/top10s?{urllib.parse.urlencode(params)}"
        print(f"  [WOULD CALL] {ep['platform']:15s} → {url}", file=sys.stderr)
    print("DRY RUN PASSED (no HTTP requests made)", file=sys.stderr)


def main() -> None:
    if "--dry-run" in sys.argv:
        dry_run()
        return

    api_key, error, masked = load_api_key()
    if error:
        print(json.dumps({"error": error}, indent=2))
        sys.exit(1)

    print(f"[INFO] API key loaded: {masked}", file=sys.stderr)

    results = []
    success_count = 0
    auth_ok = False

    for i, ep in enumerate(ENDPOINTS):
        print(
            f"[INFO] Calling {ep['platform']} ({i + 1}/{len(ENDPOINTS)})...",
            file=sys.stderr,
        )
        result = call_endpoint(
            api_key, ep["platform"], ep["company"], ep["country"], ep["content_type"]
        )

        # 401/403 — stop immediately
        if result["status_code"] in (401, 403):
            masked_error = mask_key_in_text(result["error"] or "", api_key)
            print(
                f"[FATAL] Auth failure on {ep['platform']}: {masked_error}",
                file=sys.stderr,
            )
            results.append(result)
            break

        # 429 — backoff 5s, retry once
        if result["status_code"] == 429:
            print(
                f"[WARN] Rate limited on {ep['platform']}, backing off 5s...",
                file=sys.stderr,
            )
            time.sleep(5)
            result = call_endpoint(
                api_key,
                ep["platform"],
                ep["company"],
                ep["country"],
                ep["content_type"],
            )
            if result["status_code"] == 429:
                print(
                    f"[WARN] Still rate limited on {ep['platform']}, skipping",
                    file=sys.stderr,
                )

        if result["status_code"] == 200:
            success_count += 1
            auth_ok = True
            print(
                f"[OK] {ep['platform']}: {result['item_count']} items, "
                f"{result['response_time_ms']}ms",
                file=sys.stderr,
            )
        elif result["error"]:
            masked_error = mask_key_in_text(result["error"], api_key)
            print(
                f"[FAIL] {ep['platform']}: HTTP {result['status_code']} — {masked_error}",
                file=sys.stderr,
            )

        results.append(result)

        # Respect rate limit: ≥ 1s between calls (conservative)
        if i < len(ENDPOINTS) - 1:
            time.sleep(1)

    # Determine coverage and field status
    all_required_fields = set(REQUIRED_FIELDS.keys())
    missing_any_field = False
    for r in results:
        if r["fields_missing_vs_required"]:
            missing_any_field = True
            break

    summary = {
        "total_endpoints": len(ENDPOINTS),
        "success": success_count,
        "auth_ok": auth_ok,
        "platform_coverage_ok": success_count == len(ENDPOINTS),
        "required_fields_all_present": not missing_any_field,
    }

    output = {
        "run_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "auth": {
            "key_loaded_from": SECRETS_PATH,
            "key_present": True,
            "key_masked": masked,
        },
        "endpoints": results,
        "summary": summary,
    }

    # Sanitize: remove any raw key that might have leaked into output
    output_str = json.dumps(output, indent=2, ensure_ascii=False)
    output_str = mask_key_in_text(output_str, api_key)
    print(output_str)


if __name__ == "__main__":
    main()
