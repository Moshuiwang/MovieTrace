from __future__ import annotations

import json
import re
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0"
)


def get_json(
    url: str,
    *,
    params: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
    timeout: int = 20,
    log_context: dict | None = None,
) -> object:
    full_url = url
    if params:
        full_url = f"{url}?{urlencode(params)}"
    merged_headers = {"User-Agent": DEFAULT_USER_AGENT}
    if headers:
        merged_headers.update(headers)
    request = Request(full_url, headers=merged_headers)
    start = time.monotonic()
    try:
        with urlopen(request, timeout=timeout) as response:
            http_status = response.status
            body = response.read().decode("utf-8")
        result = json.loads(body)
        elapsed_ms = int((time.monotonic() - start) * 1000)
        _log_success(log_context, http_status, elapsed_ms, result)
        return result
    except Exception as exc:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        _log_error(log_context, exc, elapsed_ms)
        raise


def _log_success(
    log_context: dict | None,
    http_status: int,
    duration_ms: int,
    result: object,
) -> None:
    if not log_context:
        return
    try:
        from movietrace.logging.api_usage import log_api_call

        item_count = None
        if isinstance(result, dict):
            data = result.get("data")
            results = result.get("results")
            if isinstance(data, list):
                item_count = len(data)
            elif isinstance(results, list):
                item_count = len(results)
        elif isinstance(result, list):
            item_count = len(result)

        log_api_call(
            db_path=log_context["db_path"],
            service=log_context["service"],
            endpoint=log_context["endpoint"],
            operation=log_context.get("operation"),
            request_date=log_context["request_date"],
            status="success",
            http_status=http_status,
            duration_ms=duration_ms,
            item_count=item_count,
            key_fingerprint=log_context.get("key_fingerprint", ""),
            metadata=log_context.get("metadata"),
        )
    except Exception:
        pass


def _log_error(
    log_context: dict | None,
    exc: Exception,
    duration_ms: int,
) -> None:
    if not log_context:
        return
    try:
        from movietrace.logging.api_usage import log_api_call

        error_msg = str(exc)
        http_status = None
        m = re.search(r"HTTP Error (\d{3})", error_msg)
        if m:
            http_status = int(m.group(1))
        rate_limited = http_status == 429

        log_api_call(
            db_path=log_context["db_path"],
            service=log_context["service"],
            endpoint=log_context["endpoint"],
            operation=log_context.get("operation"),
            request_date=log_context["request_date"],
            status="http_error" if http_status else "network_error",
            http_status=http_status,
            rate_limited=rate_limited,
            duration_ms=duration_ms,
            error_code=str(http_status) if http_status else None,
            error_message=error_msg,
            key_fingerprint=log_context.get("key_fingerprint", ""),
            metadata=log_context.get("metadata"),
        )
    except Exception:
        pass

