"""Shared HTTP helpers for Feishu REST API.

All bitable sync modules (sync.py, gap_sync.py) use these helpers
to avoid duplicating boilerplate. baseline.py predates this module.
"""
from __future__ import annotations

import json
import re
import urllib.request
import urllib.error

OPEN_API_BASE = "https://open.feishu.cn/open-apis"


def request_json(
    method: str,
    url: str,
    *,
    token: str | None = None,
    payload: dict | None = None,
) -> dict:
    """Issue a JSON request, return parsed body. Raises on HTTP error."""
    headers = {"Content-Type": "application/json; charset=utf-8"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = None
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:200]
        # Mask tokens that might appear in error responses
        body = re.sub(r'"access_token"\s*:\s*"[^"]+"', '"access_token":"***"', body)
        raise RuntimeError(f"Feishu API HTTP {e.code}: {body}") from e


def batch_create_records(
    token: str,
    app_token: str,
    table_id: str,
    records: list[dict],
) -> None:
    """POST /records/batch_create, raises on code != 0."""
    url = f"{OPEN_API_BASE}/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_create"
    payload = {"records": records}
    resp = request_json("POST", url, token=token, payload=payload)
    if resp.get("code") != 0:
        raise RuntimeError(f"batch create records failed: {resp}")


def batch_update_records(
    token: str,
    app_token: str,
    table_id: str,
    updates: list[dict],
) -> None:
    """POST /records/batch_update with [{record_id, fields}, ...], raises on code != 0.

    Endpoint: POST /bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_update
    Payload: {"records": [{"record_id": "...", "fields": {...}}, ...]}
    Limit: 500 records per call (split larger lists into chunks).
    """
    url = f"{OPEN_API_BASE}/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_update"
    chunk_size = 500
    for start in range(0, len(updates), chunk_size):
        chunk = updates[start : start + chunk_size]
        resp = request_json("POST", url, token=token, payload={"records": chunk})
        if resp.get("code") != 0:
            raise RuntimeError(f"batch update records failed: {resp}")


def unwrap_text_field(value) -> str:
    """Unwrap a Feishu rich-text field value to a plain string.

    The API may return text fields as either a plain str or a list of
    {'text': str, 'type': str} segments. Return str either way.
    """
    if isinstance(value, list):
        return "".join(seg.get("text", "") for seg in value)
    return str(value) if value is not None else ""
