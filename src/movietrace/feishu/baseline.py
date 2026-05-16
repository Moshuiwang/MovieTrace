from __future__ import annotations

import json
import time
import urllib.parse
from pathlib import Path

from movietrace.feishu._http import request_json as _request_json

OPEN_API_BASE = "https://open.feishu.cn/open-apis"


def _fetch_token_uncached(app_id: str, app_secret: str) -> tuple[str, int]:
    """Fetch a fresh tenant_access_token from Feishu. Returns (token, expire_seconds)."""
    response = _request_json(
        "POST",
        f"{OPEN_API_BASE}/auth/v3/tenant_access_token/internal",
        payload={"app_id": app_id, "app_secret": app_secret},
    )
    if response.get("code") != 0:
        raise RuntimeError(f"Feishu token request failed: {response}")
    token = str(response["tenant_access_token"])
    expire = int(response.get("expire", 7200))
    return token, expire


def fetch_tenant_access_token(app_id: str, app_secret: str) -> str:
    """Fetch Feishu tenant_access_token, with file-based cache (5 min skew before expiry).

    Cache is stored at ~/.cache/movietrace/feishu_token.json with mode 0600.
    Multiple CLI invocations within the same session reuse the cached token.
    """
    cache_path = Path.home() / ".cache/movietrace/feishu_token.json"
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    # Try to read a fresh cache entry
    if cache_path.exists():
        try:
            cached = json.loads(cache_path.read_text())
            if cached.get("app_id") == app_id and cached.get("expires_at", 0) > time.time() + 300:
                return cached["token"]
        except (json.JSONDecodeError, KeyError, OSError):
            pass

    # Cache miss — fetch a fresh token
    token, expire = _fetch_token_uncached(app_id, app_secret)

    # Persist cache (Feishu tokens last ~2 h by default)
    expires_at = time.time() + expire
    try:
        cache_path.write_text(json.dumps({
            "app_id": app_id,
            "token": token,
            "expires_at": expires_at,
        }))
        cache_path.chmod(0o600)
    except OSError:
        pass  # Cache write failure is non-fatal; proceed with fresh token

    return token


def fetch_bitable_records(
    *,
    tenant_access_token: str,
    app_token: str,
    table_id: str,
    page_size: int = 500,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    page_token = ""
    while True:
        params = {"page_size": str(page_size)}
        if page_token:
            params["page_token"] = page_token
        url = (
            f"{OPEN_API_BASE}/bitable/v1/apps/{app_token}/tables/"
            f"{table_id}/records?{urllib.parse.urlencode(params)}"
        )
        response = _request_json(
            "GET",
            url,
            token=tenant_access_token,
        )
        if response.get("code") != 0:
            raise RuntimeError(f"Feishu records request failed: {response}")
        data = response.get("data") or {}
        records.extend(data.get("items") or [])
        if not data.get("has_more"):
            return records
        page_token = str(data.get("page_token") or "")
        if not page_token:
            return records

