"""Shared HTTP helpers for Feishu REST API.

All bitable sync modules (sync.py, gap_sync.py) use these helpers
to avoid duplicating boilerplate. baseline.py predates this module.
"""
from __future__ import annotations

import json
import re
import secrets
import urllib.request
import urllib.error

from movietrace.sources._http_policy import HttpPolicy, request_with_policy

OPEN_API_BASE = "https://open.feishu.cn/open-apis"

# Policy for Feishu JSON calls: no 5xx auto-retry (app-layer retry in P1.45
# handles Feishu business failures; transport 5xx should surface quickly)
_FEISHU_JSON_POLICY = HttpPolicy(timeout=30.0, max_retries=0, log_to_db=False)
# Policy for media upload: longer timeout, no retry
_FEISHU_UPLOAD_POLICY = HttpPolicy(timeout=60.0, max_retries=0, log_to_db=False)


def build_multipart_body(
    fields: dict[str, "str | tuple[bytes, str, str]"],
) -> tuple[bytes, str]:
    """Build a multipart/form-data body (RFC 7578, stdlib only).

    fields values:
      - str  → plain text part
      - (data: bytes, filename: str, content_type: str) → file part

    Returns (body_bytes, boundary_string).
    """
    boundary = secrets.token_hex(16)
    sep = f"--{boundary}\r\n".encode()
    end = f"--{boundary}--\r\n".encode()

    parts: list[bytes] = []
    for name, value in fields.items():
        if isinstance(value, tuple):
            data, filename, ctype = value
            header = (
                f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'
                f"Content-Type: {ctype}\r\n\r\n"
            ).encode("utf-8")
            parts.append(sep + header + data + b"\r\n")
        else:
            header = f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8")
            parts.append(sep + header + value.encode("utf-8") + b"\r\n")

    return b"".join(parts) + end, boundary


def upload_media_file(
    token: str,
    file_name: str,
    file_data: bytes,
    *,
    extra: dict | None = None,
) -> str:
    """Upload a file via drive/v1/medias/upload_all, return file_token.

    Uses parent_type="ccm_import_open" required for import tasks.
    extra defaults to {"obj_type": "docx", "file_extension": "md"}.
    """
    if extra is None:
        extra = {"obj_type": "docx", "file_extension": "md"}

    fields: dict[str, "str | tuple[bytes, str, str]"] = {
        "file_name": file_name,
        "parent_type": "ccm_import_open",
        "size": str(len(file_data)),
        "extra": json.dumps(extra, ensure_ascii=False),
        "file": (file_data, file_name, "application/octet-stream"),
    }
    body, boundary = build_multipart_body(fields)

    url = f"{OPEN_API_BASE}/drive/v1/medias/upload_all"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": f"multipart/form-data; boundary={boundary}",
    }
    status, resp_body, _resp_headers = request_with_policy(
        url,
        method="POST",
        headers=headers,
        data=body,
        policy=_FEISHU_UPLOAD_POLICY,
    )
    if status >= 400:
        body_err = resp_body.decode("utf-8", errors="replace")[:300]
        body_err = re.sub(r'"access_token"\s*:\s*"[^"]+"', '"access_token":"***"', body_err)
        raise RuntimeError(f"Feishu upload_all HTTP {status}: {body_err}")
    result = json.loads(resp_body.decode("utf-8"))

    if result.get("code") != 0:
        code = result.get("code")
        msg = result.get("msg", "")
        if code in (99991663, 99991661, 1061045):
            raise RuntimeError(
                f"Feishu upload permission denied (code={code}): {msg}. "
                "Grant the app 'drive:drive' scope in the Feishu console."
            )
        raise RuntimeError(f"Feishu upload_all failed (code={code}): {msg}")

    file_token = result.get("data", {}).get("file_token", "")
    if not file_token:
        raise RuntimeError(f"Feishu upload_all returned no file_token: {result}")
    return file_token


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
    status, resp_body, _resp_headers = request_with_policy(
        url,
        method=method,
        headers=headers,
        data=data,
        policy=_FEISHU_JSON_POLICY,
    )
    if status >= 400:
        body = resp_body.decode("utf-8", errors="replace")[:200]
        # Mask tokens that might appear in error responses
        body = re.sub(r'"access_token"\s*:\s*"[^"]+"', '"access_token":"***"', body)
        raise RuntimeError(f"Feishu API HTTP {status}: {body}")
    return json.loads(resp_body.decode("utf-8"))


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


def batch_delete_records(
    token: str,
    app_token: str,
    table_id: str,
    record_ids: list[str],
) -> None:
    """POST /records/batch_delete, raises on code != 0. Chunks to 500."""
    url = f"{OPEN_API_BASE}/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_delete"
    chunk_size = 500
    for start in range(0, len(record_ids), chunk_size):
        chunk = record_ids[start : start + chunk_size]
        resp = request_json("POST", url, token=token, payload={"records": chunk})
        if resp.get("code") != 0:
            raise RuntimeError(f"batch delete records failed: {resp}")


def unwrap_text_field(value) -> str:
    """Unwrap a Feishu rich-text field value to a plain string.

    The API may return text fields as either a plain str or a list of
    {'text': str, 'type': str} segments. Return str either way.
    """
    if isinstance(value, list):
        return "".join(seg.get("text", "") for seg in value)
    return str(value) if value is not None else ""
