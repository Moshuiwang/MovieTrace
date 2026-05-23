"""Tests for the shared HTTP policy layer (P1.46)."""
from __future__ import annotations

import sys
import unittest
from http.client import HTTPMessage
from pathlib import Path
from unittest.mock import MagicMock, call, patch
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

_URLOPEN_PATH = "movietrace.sources._http_policy.urlopen"
_SLEEP_PATH = "movietrace.sources._http_policy.time.sleep"
_LOG_API_CALL_PATH = "movietrace.logging.api_usage.log_api_call"


def _make_mock_response(
    status: int = 200,
    body: bytes = b'{"ok": true}',
    content_encoding: str | None = None,
) -> MagicMock:
    """Build a mock urlopen context-manager response."""
    headers = HTTPMessage()
    if content_encoding:
        headers["Content-Encoding"] = content_encoding

    mock_resp = MagicMock()
    mock_resp.status = status
    mock_resp.read.return_value = body
    mock_resp.headers = headers

    mock_ctx = MagicMock()
    mock_ctx.__enter__ = MagicMock(return_value=mock_resp)
    mock_ctx.__exit__ = MagicMock(return_value=False)
    return mock_ctx


def _make_http_error(
    status: int,
    reason: str = "Error",
    headers: dict | None = None,
    body: bytes = b"",
) -> HTTPError:
    """Build an HTTPError with optional headers dict."""
    msg = HTTPMessage()
    if headers:
        for k, v in headers.items():
            msg[k] = v
    exc = HTTPError("https://example.com", status, reason, msg, None)
    # Patch read() so _read_http_error can read the body
    exc.read = lambda: body  # type: ignore[method-assign]
    return exc


def _make_log_context() -> dict[str, str]:
    return {
        "db_path": ":memory:",
        "service": "tmdb",
        "endpoint": "/tv/1",
        "operation": "test",
        "request_date": "2026-05-23",
        "key_fingerprint": "abc123",
    }


class TestRequestWithPolicy(unittest.TestCase):

    def test_request_with_policy_returns_2xx_directly(self):
        """200 response is returned immediately with a single urlopen call."""
        from movietrace.sources._http_policy import request_with_policy

        mock_ctx = _make_mock_response(200, b'{"result": 1}')
        with patch(_URLOPEN_PATH, return_value=mock_ctx) as mock_urlopen, \
             patch(_SLEEP_PATH) as mock_sleep:
            status, body, resp_headers = request_with_policy("https://example.com/api")

        self.assertEqual(status, 200)
        self.assertEqual(body, b'{"result": 1}')
        mock_urlopen.assert_called_once()
        mock_sleep.assert_not_called()

    def test_request_with_policy_retries_on_503(self):
        """503 triggers retry; succeeds on 3rd attempt (2 retries)."""
        from movietrace.sources._http_policy import HttpPolicy, request_with_policy

        policy = HttpPolicy(max_retries=3, backoff_base=0.01)
        err_503 = _make_http_error(503)

        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise err_503
            return _make_mock_response(200, b'{"ok": true}')

        with patch(_URLOPEN_PATH, side_effect=side_effect), \
             patch(_SLEEP_PATH):
            status, body, _ = request_with_policy(
                "https://example.com/api", policy=policy
            )

        self.assertEqual(status, 200)
        self.assertEqual(call_count, 3)

    def test_request_with_policy_gives_up_after_max_retries(self):
        """When all retries return 503, RuntimeError is raised."""
        from movietrace.sources._http_policy import HttpPolicy, request_with_policy

        policy = HttpPolicy(max_retries=3, backoff_base=0.01)
        err_503 = _make_http_error(503)

        with patch(_URLOPEN_PATH, side_effect=err_503), \
             patch(_SLEEP_PATH):
            with self.assertRaises(RuntimeError) as ctx:
                request_with_policy("https://example.com/api", policy=policy)

        self.assertIn("retries", str(ctx.exception).lower())

    def test_request_with_policy_respects_retry_after_seconds(self):
        """429 with Retry-After: 2 causes sleep of ~2 seconds."""
        from movietrace.sources._http_policy import HttpPolicy, request_with_policy

        policy = HttpPolicy(max_retries=1, backoff_base=0.01)
        err_429 = _make_http_error(429, headers={"Retry-After": "2"})
        mock_200 = _make_mock_response(200)

        with patch(_URLOPEN_PATH) as mock_urlopen, \
             patch(_SLEEP_PATH) as mock_sleep:
            mock_urlopen.side_effect = [err_429, mock_200]
            status, _, _ = request_with_policy(
                "https://example.com/api", policy=policy
            )

        self.assertEqual(status, 200)
        # First sleep call should be the Retry-After wait (2s)
        sleep_calls = mock_sleep.call_args_list
        self.assertTrue(any(abs(c.args[0] - 2.0) < 0.1 for c in sleep_calls),
                        f"Expected sleep ~2s, got calls: {sleep_calls}")

    def test_request_with_policy_ignores_retry_after_above_60(self):
        """429 with Retry-After: 300 is returned immediately (above 60s cap)."""
        from movietrace.sources._http_policy import HttpPolicy, request_with_policy

        policy = HttpPolicy(max_retries=3, backoff_base=0.01)
        err_429 = _make_http_error(429, headers={"Retry-After": "300"})

        with patch(_URLOPEN_PATH, side_effect=err_429) as mock_urlopen, \
             patch(_SLEEP_PATH) as mock_sleep:
            status, _, _ = request_with_policy(
                "https://example.com/api", policy=policy
            )

        self.assertEqual(status, 429)
        # Only one urlopen call — returned immediately
        mock_urlopen.assert_called_once()
        # No sleep for the Retry-After (returned before sleeping)
        mock_sleep.assert_not_called()

    def test_request_with_policy_does_not_retry_4xx_except_429(self):
        """404 is returned immediately without retry."""
        from movietrace.sources._http_policy import HttpPolicy, request_with_policy

        policy = HttpPolicy(max_retries=3, backoff_base=0.01)
        err_404 = _make_http_error(404)

        with patch(_URLOPEN_PATH, side_effect=err_404) as mock_urlopen, \
             patch(_SLEEP_PATH) as mock_sleep:
            status, _, _ = request_with_policy(
                "https://example.com/api", policy=policy
            )

        self.assertEqual(status, 404)
        mock_urlopen.assert_called_once()
        mock_sleep.assert_not_called()

    def test_request_with_policy_retries_on_network_error(self):
        """URLError causes retry; succeeds on 3rd attempt."""
        from movietrace.sources._http_policy import HttpPolicy, request_with_policy

        policy = HttpPolicy(max_retries=3, backoff_base=0.01)
        net_err = URLError("connection refused")

        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise net_err
            return _make_mock_response(200, b'{"ok": true}')

        with patch(_URLOPEN_PATH, side_effect=side_effect), \
             patch(_SLEEP_PATH):
            status, body, _ = request_with_policy(
                "https://example.com/api", policy=policy
            )

        self.assertEqual(status, 200)
        self.assertEqual(call_count, 3)

    def test_request_with_policy_skips_db_log_when_disabled(self):
        """HttpPolicy(log_to_db=False) suppresses transport DB logging."""
        from movietrace.sources._http_policy import HttpPolicy, request_with_policy

        policy = HttpPolicy(log_to_db=False)
        mock_ctx = _make_mock_response(200, b'{"ok": true}')

        with patch(_URLOPEN_PATH, return_value=mock_ctx), \
             patch(_SLEEP_PATH), \
             patch(_LOG_API_CALL_PATH) as mock_log_api_call:
            status, _, _ = request_with_policy(
                "https://example.com/api",
                policy=policy,
                log_context=_make_log_context(),
            )

        self.assertEqual(status, 200)
        mock_log_api_call.assert_not_called()

    def test_request_with_policy_writes_db_log_when_enabled(self):
        """Default HttpPolicy writes one transport DB log when log_context exists."""
        from movietrace.sources._http_policy import HttpPolicy, request_with_policy

        policy = HttpPolicy()
        mock_ctx = _make_mock_response(200, b'{"ok": true}')

        with patch(_URLOPEN_PATH, return_value=mock_ctx), \
             patch(_SLEEP_PATH), \
             patch(_LOG_API_CALL_PATH) as mock_log_api_call:
            status, _, _ = request_with_policy(
                "https://example.com/api",
                policy=policy,
                log_context=_make_log_context(),
            )

        self.assertEqual(status, 200)
        mock_log_api_call.assert_called_once()


if __name__ == "__main__":
    unittest.main()
