"""API usage logging helper — writes to api_usage_log table.

All writes are best-effort: failures are logged as warnings and never
propagated to the caller, so logging can't break the main pipeline.
"""

from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
import time
from pathlib import Path

logger = logging.getLogger("movietrace.logging.api_usage")

# Max length for error messages to avoid bloat
MAX_ERROR_LEN = 500


def fingerprint_key(raw: str) -> str:
    """SHA-256 hex digest, first 12 chars. Irreversible. Never stores the raw key."""
    if not raw:
        return ""
    return hashlib.sha256(raw.encode()).hexdigest()[:12]


def log_api_call(
    db_path: str | Path,
    *,
    service: str,
    endpoint: str,
    operation: str | None = None,
    request_date: str,
    status: str,
    http_status: int | None = None,
    cache_status: str | None = None,
    quota_error: bool = False,
    rate_limited: bool = False,
    duration_ms: int | None = None,
    item_count: int | None = None,
    error_code: str | None = None,
    error_message: str | None = None,
    key_fingerprint: str = "",
    metadata: dict | None = None,
) -> None:
    """Write one row to api_usage_log. Best-effort — never raises."""
    if error_message and len(error_message) > MAX_ERROR_LEN:
        error_message = error_message[:MAX_ERROR_LEN]
    metadata_json = None
    if metadata:
        # Ensure no keys leak into metadata
        safe = _sanitize_metadata(metadata)
        metadata_json = json.dumps(safe, ensure_ascii=False)
    try:
        conn = sqlite3.connect(str(db_path))
        conn.execute("pragma foreign_keys = on")
        conn.execute(
            """insert into api_usage_log(
                service, endpoint, operation, request_date, status,
                http_status, cache_status, quota_error, rate_limited,
                duration_ms, item_count, error_code, error_message,
                key_fingerprint, metadata_json
            ) values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                service,
                endpoint,
                operation,
                request_date,
                status,
                http_status,
                cache_status,
                1 if quota_error else 0,
                1 if rate_limited else 0,
                duration_ms,
                item_count,
                error_code,
                error_message,
                key_fingerprint,
                metadata_json,
            ),
        )
        conn.commit()
        conn.close()
    except Exception:
        logger.warning("Failed to write api_usage_log row", exc_info=True)


# Fields that must never appear in metadata
_FORBIDDEN_META_KEYS = {
    "apikey", "api_key", "api-key", "authorization",
    "bearer", "token", "access_token", "secret", "password",
    "key", "credentials",
}


def _sanitize_metadata(meta: dict) -> dict:
    """Remove any key-like fields from metadata before writing."""
    safe = {}
    for k, v in meta.items():
        kl = k.lower().replace("_", "").replace("-", "")
        if kl in _FORBIDDEN_META_KEYS:
            continue
        if isinstance(v, str) and len(v) > 200:
            safe[k] = v[:200] + "..."
        else:
            safe[k] = v
    return safe


class ApiCallTracker:
    """Context-manager style tracker for a single API call.

    Usage:
        tracker = ApiCallTracker(db_path, service="tmdb", ...)
        tracker.start()
        try:
            result = get_json(...)
            tracker.mark_success(item_count=len(result))
        except Exception as e:
            tracker.mark_error(e)
            raise
    """

    def __init__(
        self,
        db_path: str | Path,
        *,
        service: str,
        endpoint: str,
        operation: str | None = None,
        request_date: str,
        key_fingerprint: str = "",
        metadata: dict | None = None,
    ):
        self.db_path = db_path
        self.service = service
        self.endpoint = endpoint
        self.operation = operation
        self.request_date = request_date
        self.key_fingerprint = key_fingerprint
        self.metadata = metadata
        self._start: float | None = None

    def start(self) -> None:
        self._start = time.monotonic()

    @property
    def elapsed_ms(self) -> int | None:
        if self._start is None:
            return None
        return int((time.monotonic() - self._start) * 1000)

    def mark_success(
        self,
        http_status: int = 200,
        item_count: int | None = None,
    ) -> None:
        log_api_call(
            db_path=self.db_path,
            service=self.service,
            endpoint=self.endpoint,
            operation=self.operation,
            request_date=self.request_date,
            status="success",
            http_status=http_status,
            duration_ms=self.elapsed_ms,
            item_count=item_count,
            key_fingerprint=self.key_fingerprint,
            metadata=self.metadata,
        )

    def mark_error(
        self,
        exc: Exception,
        http_status: int | None = None,
        quota_error: bool = False,
        rate_limited: bool = False,
    ) -> None:
        error_msg = str(exc)
        # Detect HTTP status from urllib error message pattern
        import re
        if http_status is None:
            m = re.search(r"HTTP Error (\d{3})", error_msg)
            if m:
                http_status = int(m.group(1))

        log_api_call(
            db_path=self.db_path,
            service=self.service,
            endpoint=self.endpoint,
            operation=self.operation,
            request_date=self.request_date,
            status="http_error" if http_status else "network_error",
            http_status=http_status,
            quota_error=quota_error,
            rate_limited=rate_limited,
            duration_ms=self.elapsed_ms,
            error_code=str(http_status) if http_status else None,
            error_message=error_msg,
            key_fingerprint=self.key_fingerprint,
            metadata=self.metadata,
        )
