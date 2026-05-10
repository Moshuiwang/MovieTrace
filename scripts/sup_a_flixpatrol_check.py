#!/usr/bin/env python3
"""
SUP-A FlixPatrol Accessibility Check
Validates FlixPatrol public page accessibility for V1 data sourcing.
stdlib only — no external dependencies.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.robotparser import RobotFileParser

USER_AGENT = "Mozilla/5.0 (compatible; MovieTraceBot/0.1; +accessibility-verification)"
TIMEOUT = 20
REQUEST_INTERVAL = 3
MAX_RETRIES = 1

BASE_URL = "https://flixpatrol.com"
ROBOTS_URL = f"{BASE_URL}/robots.txt"

TARGET_URLS = [
    {"name": "netflix_global",     "url": f"{BASE_URL}/top10/netflix/",               "priority": "required"},
    {"name": "netflix_us",         "url": f"{BASE_URL}/top10/netflix/united-states/",  "priority": "required"},
    {"name": "amazon_prime_world", "url": f"{BASE_URL}/top10/amazon-prime/world/",     "priority": "high"},
    {"name": "disney_world",       "url": f"{BASE_URL}/top10/disney/world/",           "priority": "high"},
    {"name": "apple_tv_world",     "url": f"{BASE_URL}/top10/apple-tv/world/",         "priority": "medium"},
    {"name": "hbo_us",             "url": f"{BASE_URL}/top10/hbo/united-states/",      "priority": "medium"},
    {"name": "hulu_us",            "url": f"{BASE_URL}/top10/hulu/united-states/",     "priority": "medium"},
]

SCRIPTS_DIR = pathlib.Path(__file__).parent
PROJECT_ROOT = SCRIPTS_DIR.parent
FIXTURES_DIR = PROJECT_ROOT / "tests" / "fixtures" / "flixpatrol"
ROBOTS_FILE  = PROJECT_ROOT / "data" / "flixpatrol_robots.txt"
REPORTS_DIR  = PROJECT_ROOT / "reports"


def check_environment() -> None:
    if sys.version_info < (3, 10):
        print("ERROR: Python 3.10+ required", file=sys.stderr)
        sys.exit(2)
    for d in [FIXTURES_DIR, REPORTS_DIR, ROBOTS_FILE.parent]:
        d.mkdir(parents=True, exist_ok=True)
    print("Environment check passed.", file=sys.stderr)


def fetch_url(url: str, *, save_html: bool = False, html_name: str | None = None) -> dict:
    result: dict = {
        "url": url,
        "status_code": None,
        "response_time_ms": None,
        "content_length": None,
        "content_type": None,
        "final_url": None,
        "html_saved_to": None,
        "error": None,
    }
    for attempt in range(MAX_RETRIES + 1):
        start = time.monotonic()
        try:
            req = Request(url, headers={"User-Agent": USER_AGENT})
            with urlopen(req, timeout=TIMEOUT) as resp:
                elapsed_ms = int((time.monotonic() - start) * 1000)
                body = resp.read()
                result.update({
                    "status_code": resp.status,
                    "response_time_ms": elapsed_ms,
                    "content_length": len(body),
                    "content_type": resp.headers.get("Content-Type"),
                    "final_url": resp.url,
                    "error": None,
                })
                if save_html and html_name and resp.status == 200:
                    html_path = FIXTURES_DIR / html_name
                    html_path.write_bytes(body)
                    result["html_saved_to"] = str(html_path.relative_to(PROJECT_ROOT))
                break
        except HTTPError as e:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            result.update({
                "status_code": e.code,
                "response_time_ms": elapsed_ms,
                "error": f"HTTPError: {e.code} {e.reason}",
            })
            break
        except URLError as e:
            if attempt < MAX_RETRIES:
                time.sleep(REQUEST_INTERVAL)
                continue
            result["error"] = f"URLError: {e.reason}"
        except Exception as e:
            result["error"] = f"{type(e).__name__}: {e}"
            break
    return result


def fetch_robots_txt() -> dict:
    print("Checking robots.txt ...", file=sys.stderr)
    robots_result: dict = {
        "fetched": False,
        "status_code": None,
        "raw_content": None,
        "crawl_delay": None,
        "allows_target_paths": [],
        "error": None,
    }
    try:
        req = Request(ROBOTS_URL, headers={"User-Agent": USER_AGENT})
        with urlopen(req, timeout=TIMEOUT) as resp:
            content = resp.read().decode("utf-8", errors="replace")
            robots_result.update({"fetched": True, "status_code": resp.status, "raw_content": content})
            ROBOTS_FILE.write_text(content, encoding="utf-8")
            print(f"  Saved robots.txt → {ROBOTS_FILE}", file=sys.stderr)
    except Exception as e:
        robots_result["error"] = str(e)
        print(f"  WARNING: could not fetch robots.txt: {e}", file=sys.stderr)
        return robots_result

    # Parse the already-fetched content instead of rp.read() (which makes a
    # second request with Python's default User-Agent and may get 403→disallow_all=True)
    rp = RobotFileParser()
    rp.set_url(ROBOTS_URL)
    rp.parse(content.splitlines())
    robots_result["crawl_delay"] = rp.crawl_delay(USER_AGENT)

    for target in TARGET_URLS:
        allowed = rp.can_fetch(USER_AGENT, target["url"])
        robots_result["allows_target_paths"].append({
            "name": target["name"],
            "path": urlparse(target["url"]).path,
            "url": target["url"],
            "allowed": allowed,
        })
        icon = "✅" if allowed else "❌"
        print(f"  {icon} robots {'allows' if allowed else 'DISALLOWS'}: {target['url']}", file=sys.stderr)

    return robots_result


def run_checks(dry_run: bool = False) -> dict:
    run_at = datetime.now(timezone.utc).isoformat()
    print(f"\n=== SUP-A FlixPatrol Accessibility Check ===", file=sys.stderr)
    print(f"Run at : {run_at}", file=sys.stderr)
    print(f"Mode   : {'DRY-RUN (robots.txt only)' if dry_run else 'FULL'}", file=sys.stderr)

    robots_result = fetch_robots_txt()
    time.sleep(REQUEST_INTERVAL)

    empty_summary = {"total_urls": 0, "success": 0, "client_error_4xx": 0,
                     "server_error_5xx": 0, "network_error": 0, "robots_disallowed": 0}

    if dry_run:
        return {"run_at": run_at, "dry_run": True,
                "robots_txt": robots_result, "url_checks": [], "summary": empty_summary}

    allowed_map = {item["url"]: item["allowed"]
                   for item in robots_result.get("allows_target_paths", [])}

    url_checks: list[dict] = []
    robots_disallowed = 0

    for target in TARGET_URLS:
        url, name = target["url"], target["name"]

        if not allowed_map.get(url, True):
            print(f"\nSKIP (robots disallows): {url}", file=sys.stderr)
            url_checks.append({
                "url": url, "name": name, "priority": target["priority"],
                "status_code": None, "response_time_ms": None,
                "content_length": None, "content_type": None,
                "final_url": None, "html_saved_to": None,
                "robots_allowed": False,
                "error": "robots.txt disallows this path",
            })
            robots_disallowed += 1
            continue

        print(f"\n[{target['priority']}] {url}", file=sys.stderr)
        result = fetch_url(url, save_html=True, html_name=f"{name}.html")
        result["name"] = name
        result["priority"] = target["priority"]
        result["robots_allowed"] = True
        url_checks.append(result)

        line = f"  → {result['status_code']}"
        if result["response_time_ms"] is not None:
            line += f"  {result['response_time_ms']} ms"
        if result["content_length"] is not None:
            line += f"  {result['content_length']:,} bytes"
        if result["error"]:
            line += f"  ERR: {result['error']}"
        if result["html_saved_to"]:
            line += f"  saved ✓"
        print(line, file=sys.stderr)

        time.sleep(REQUEST_INTERVAL)

    success        = sum(1 for r in url_checks if r.get("status_code") == 200)
    client_errors  = sum(1 for r in url_checks if r.get("status_code") and 400 <= r["status_code"] < 500)
    server_errors  = sum(1 for r in url_checks if r.get("status_code") and r["status_code"] >= 500)
    network_errors = sum(1 for r in url_checks if r.get("error") and not r.get("status_code"))

    print(f"\n=== Summary ===", file=sys.stderr)
    print(f"Success      : {success}/{len(TARGET_URLS)}", file=sys.stderr)
    print(f"4xx          : {client_errors}", file=sys.stderr)
    print(f"5xx          : {server_errors}", file=sys.stderr)
    print(f"Network err  : {network_errors}", file=sys.stderr)
    print(f"Robots block : {robots_disallowed}", file=sys.stderr)

    return {
        "run_at": run_at,
        "dry_run": False,
        "robots_txt": robots_result,
        "url_checks": url_checks,
        "summary": {
            "total_urls": len(TARGET_URLS),
            "success": success,
            "client_error_4xx": client_errors,
            "server_error_5xx": server_errors,
            "network_error": network_errors,
            "robots_disallowed": robots_disallowed,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="SUP-A: FlixPatrol public page accessibility verification (stdlib only)"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Check robots.txt only; do not fetch HTML pages")
    args = parser.parse_args()

    check_environment()
    results = run_checks(dry_run=args.dry_run)
    print(json.dumps(results, indent=2, ensure_ascii=False))

    s = results["summary"]
    if s["total_urls"] == 0:
        sys.exit(0)
    elif s["success"] == 0 and s["total_urls"] > 0:
        sys.exit(2)
    elif s["success"] < s["total_urls"]:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
