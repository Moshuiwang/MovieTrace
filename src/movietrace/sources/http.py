from __future__ import annotations

import gzip
import json
import re
import time
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from movietrace.sources._http_policy import HttpPolicy, request_with_policy

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0"
)

# Default policy for sources/http — timeout comes from HttpPolicy.timeout
_DEFAULT_SOURCES_POLICY = HttpPolicy()


class FatalApiError(RuntimeError):
    """Raised when API returns 401/402/403 — triggers circuit breaker."""
    def __init__(self, status_code: int, message: str = ""):
        self.status_code = status_code
        super().__init__(message or f"Fatal API error: HTTP {status_code}")


def get_json(
    url: str,
    *,
    params: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
    timeout: int = 20,
    log_context: dict | None = None,
) -> object:
    merged_headers = {"User-Agent": DEFAULT_USER_AGENT}
    if headers:
        merged_headers.update(headers)

    # Build a policy that respects the caller-supplied timeout; other defaults
    # come from HttpPolicy (retry, backoff, etc.)
    policy = HttpPolicy(timeout=float(timeout))

    start = time.monotonic()
    try:
        status, raw_body, _resp_headers = request_with_policy(
            url,
            headers=merged_headers,
            params=params,
            policy=policy,
            log_context=log_context,
        )
    except RuntimeError as exc:
        # Retries exhausted for 5xx / network errors
        elapsed_ms = int((time.monotonic() - start) * 1000)
        _log_error(log_context, exc, elapsed_ms)
        raise

    elapsed_ms = int((time.monotonic() - start) * 1000)

    if status in (401, 402, 403):
        exc = HTTPError(url, status, f"HTTP {status}", {}, None)
        _log_error(log_context, exc, elapsed_ms)
        raise FatalApiError(status, str(exc))

    if status >= 400:
        exc = HTTPError(url, status, f"HTTP {status}", {}, None)
        _log_error(log_context, exc, elapsed_ms)
        raise exc

    # Decompress if needed
    raw = raw_body
    if _resp_headers.get("content-encoding") == "gzip":
        raw = gzip.decompress(raw)
    body = raw.decode("utf-8")
    result = json.loads(body)

    _log_success(log_context, status, elapsed_ms, result)
    return result


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
        if isinstance(exc, HTTPError):
            http_status = exc.code
        else:
            m = re.search(r"HTTP Error (\d{3})", error_msg)
            if m:
                http_status = int(m.group(1))
        rate_limited = http_status == 429

        # OMDb 401 is a quota/authorization error (key expired or limit reached)
        quota_error = (
            log_context
            and log_context.get("service") == "omdb"
            and http_status == 401
        )
        log_api_call(
            db_path=log_context["db_path"],
            service=log_context["service"],
            endpoint=log_context["endpoint"],
            operation=log_context.get("operation"),
            request_date=log_context["request_date"],
            status="http_error" if http_status else "network_error",
            http_status=http_status,
            quota_error=quota_error,
            rate_limited=rate_limited,
            duration_ms=duration_ms,
            error_code=str(http_status) if http_status else None,
            error_message=error_msg,
            key_fingerprint=log_context.get("key_fingerprint", ""),
            metadata=log_context.get("metadata"),
        )
    except Exception:
        pass
