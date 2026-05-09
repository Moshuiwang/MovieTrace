from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import Any


OPEN_API_BASE = "https://open.feishu.cn/open-apis"


def fetch_tenant_access_token(app_id: str, app_secret: str) -> str:
    response = _request_json(
        "POST",
        f"{OPEN_API_BASE}/auth/v3/tenant_access_token/internal",
        payload={"app_id": app_id, "app_secret": app_secret},
    )
    if response.get("code") != 0:
        raise RuntimeError(f"Feishu token request failed: {response}")
    return str(response["tenant_access_token"])


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


def _request_json(
    method: str,
    url: str,
    *,
    token: str | None = None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    headers = {"Content-Type": "application/json; charset=utf-8"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = None
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))
