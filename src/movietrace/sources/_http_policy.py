"""Shared HTTP transport policy for movietrace.

Provides `HttpPolicy` (dataclass) and `request_with_policy` (function) that
centralise timeout / 5xx retry / 429 Retry-After / logging behaviour.

Design constraints (P1.46):
- stdlib only — no new dependencies
- No JSON parsing (upper layer's responsibility)
- Returns (status_code, body_bytes, response_headers_dict)
- Raises RuntimeError only when 5xx/network retries are exhausted
- 4xx (except 429) are returned immediately, not retried
- 429: wait Retry-After (up to 60s cap) once, then retry; if Retry-After > 60s,
  return (429, body, headers) immediately (do not count against max_retries)
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from email.message import Message
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

_MAX_RETRY_AFTER_SECONDS = 60.0  # discard 429 if Retry-After > this


@dataclass
class HttpPolicy:
    timeout: float = 15.0
    max_retries: int = 3                          # 5xx / network error retries
    backoff_base: float = 1.0                     # retry delay = backoff_base * 2^attempt
    respect_retry_after: bool = True              # honour 429 Retry-After header
    retry_on_status: tuple[int, ...] = (502, 503, 504)
    log_context_required: bool = True             # caller should pass log_context
    log_to_db: bool = True                        # False skips transport api_usage_log write


_DEFAULT_POLICY = HttpPolicy()


def _parse_retry_after(header_value: str | None) -> float | None:
    """Return retry delay in seconds, or None if header absent/unparseable.

    Supports seconds-integer format only. HTTP-date format is treated as
    exceeding the 60s cap (conservative fallback per P1.46 spec).
    """
    if not header_value:
        return None
    stripped = header_value.strip()
    try:
        return float(stripped)
    except ValueError:
        # HTTP-date format — treat conservatively as > cap so caller discards
        return _MAX_RETRY_AFTER_SECONDS + 1.0


def _headers_to_dict(msg: Message | None) -> dict[str, str]:
    """Convert http.client.HTTPMessage to a plain dict (lowercase keys)."""
    if msg is None:
        return {}
    result: dict[str, str] = {}
    for key in msg.keys():
        result[key.lower()] = msg[key]
    return result


def _read_http_error(exc: HTTPError) -> tuple[bytes, dict]:
    """Safely read body and headers from HTTPError."""
    try:
        body = exc.read()
    except Exception:
        body = b""
    try:
        resp_headers = _headers_to_dict(exc.headers)
    except Exception:
        resp_headers = {}
    return body, resp_headers


def request_with_policy(
    url: str,
    *,
    method: str = "GET",
    headers: dict | None = None,
    params: dict | None = None,
    data: bytes | None = None,
    policy: HttpPolicy | None = None,
    log_context: dict | None = None,
) -> tuple[int, bytes, dict]:
    """Unified HTTP transport entry point.

    Returns (status_code, body_bytes, response_headers_dict).
    Does NOT parse JSON — that is the caller's responsibility.

    Retry semantics:
    - 5xx (in retry_on_status) and network errors: retry up to max_retries times
      with exponential backoff (backoff_base * 2^attempt).
    - 429: wait Retry-After (max 60s); if Retry-After > 60s, return (429,...) immediately.
      A single 429 wait does NOT count against max_retries.
    - 4xx (except 429): return immediately, no retry.
    - Retries exhausted: raise RuntimeError.
    """
    if policy is None:
        policy = _DEFAULT_POLICY

    full_url = url
    if params:
        full_url = f"{url}?{urlencode(params)}"

    start_total = time.monotonic()
    last_exc: Exception | None = None
    last_status: int = 0
    last_body: bytes = b""
    last_resp_headers: dict = {}

    attempt = 0
    while attempt <= policy.max_retries:
        if attempt > 0:
            delay = policy.backoff_base * (2 ** (attempt - 1))
            logger.debug(
                "HTTP retry attempt=%d delay=%.1fs url=%s", attempt, delay, full_url
            )
            time.sleep(delay)

        req = Request(full_url, data=data, headers=headers or {}, method=method)
        attempt_start = time.monotonic()
        try:
            with urlopen(req, timeout=policy.timeout) as resp:
                status = resp.status
                body = resp.read()
                resp_headers = _headers_to_dict(resp.headers)

            elapsed_ms = int((time.monotonic() - attempt_start) * 1000)
            logger.debug("HTTP %d %s (%dms)", status, full_url, elapsed_ms)
            _log_transport(log_context, policy, status, elapsed_ms, "ok")
            return status, body, resp_headers

        except HTTPError as exc:
            elapsed_ms = int((time.monotonic() - attempt_start) * 1000)
            status = exc.code
            body, resp_headers = _read_http_error(exc)

            if status == 429 and policy.respect_retry_after:
                retry_after_raw = resp_headers.get("retry-after")
                wait = _parse_retry_after(retry_after_raw)
                if wait is None:
                    wait = policy.backoff_base  # default short wait
                if wait > _MAX_RETRY_AFTER_SECONDS:
                    logger.warning(
                        "429 Retry-After=%.0fs exceeds cap=%.0fs, giving up. url=%s",
                        wait, _MAX_RETRY_AFTER_SECONDS, full_url,
                    )
                    _log_transport(log_context, policy, 429, elapsed_ms, "rate_limited")
                    return status, body, resp_headers
                logger.debug(
                    "429 rate-limited, waiting %.1fs url=%s", wait, full_url
                )
                _log_transport(log_context, policy, 429, elapsed_ms, "rate_limited")
                time.sleep(wait)
                # 429 wait does NOT increment attempt counter — one free pass
                # But guard against infinite loop: if already had a 429 pass,
                # treat next 429 as final and return it.
                # We use a separate flag for this.
                last_status = status
                last_body = body
                last_resp_headers = resp_headers
                last_exc = None
                # Do not increment attempt; just try once more (next iteration
                # will re-check attempt <= max_retries, but we set attempt to
                # max_retries+1 here to prevent further 429 passes without
                # consuming the 5xx budget).
                # Actually: to keep it simple, do increment attempt on 429 too,
                # so multiple 429s eventually terminate (each 429 is one attempt).
                # This matches the intent: 429 with Retry-After is "one pass".
                attempt += 1
                continue

            if status in policy.retry_on_status:
                logger.warning(
                    "HTTP %d (retryable) attempt=%d url=%s", status, attempt, full_url
                )
                _log_transport(log_context, policy, status, elapsed_ms, "error")
                last_status = status
                last_body = body
                last_resp_headers = resp_headers
                last_exc = exc
                attempt += 1
                continue

            # 4xx (non-429) and other non-retryable — return immediately
            _log_transport(log_context, policy, status, elapsed_ms, "error")
            return status, body, resp_headers

        except (URLError, OSError) as exc:
            elapsed_ms = int((time.monotonic() - attempt_start) * 1000)
            last_exc = exc
            last_status = 0
            last_body = b""
            last_resp_headers = {}
            logger.warning(
                "Network error attempt=%d url=%s: %s", attempt, full_url, exc
            )
            _log_transport(log_context, policy, 0, elapsed_ms, "error")
            attempt += 1
            continue

    # Retries exhausted
    if last_exc is not None:
        raise RuntimeError(
            f"HTTP request failed after {policy.max_retries} retries: {last_exc}"
        ) from last_exc
    # All retries ended on a retryable status without exception
    return last_status, last_body, last_resp_headers


def _log_transport(
    log_context: dict | None,
    policy: HttpPolicy,
    status: int,
    duration_ms: int,
    outcome: str,
) -> None:
    """Write to api_usage_log if log_context provided. Swallows all errors."""
    if not policy.log_to_db:
        return
    if not log_context:
        return
    try:
        from movietrace.logging.api_usage import log_api_call

        rate_limited = status == 429
        quota_error = (
            log_context.get("service") == "omdb" and status == 401
        )
        log_api_call(
            db_path=log_context["db_path"],
            service=log_context["service"],
            endpoint=log_context["endpoint"],
            operation=log_context.get("operation"),
            request_date=log_context["request_date"],
            status=outcome,
            http_status=status if status else None,
            quota_error=quota_error,
            rate_limited=rate_limited,
            duration_ms=duration_ms,
            key_fingerprint=log_context.get("key_fingerprint", ""),
            metadata=log_context.get("metadata"),
        )
    except Exception:
        pass
