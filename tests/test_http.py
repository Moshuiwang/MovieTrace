from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
from urllib.error import HTTPError
from http.client import HTTPMessage

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

# urlopen is now called from _http_policy; patch there so mock takes effect
_URLOPEN_PATH = "movietrace.sources._http_policy.urlopen"
_SLEEP_PATH = "movietrace.sources._http_policy.time.sleep"
_LOG_API_CALL_PATH = "movietrace.logging.api_usage.log_api_call"


def _make_mock_response(status: int = 200, body: bytes = b'{"results": [1, 2]}') -> MagicMock:
    headers = HTTPMessage()
    mock_resp = MagicMock()
    mock_resp.status = status
    mock_resp.read.return_value = body
    mock_resp.headers = headers

    mock_ctx = MagicMock()
    mock_ctx.__enter__ = MagicMock(return_value=mock_resp)
    mock_ctx.__exit__ = MagicMock(return_value=False)
    return mock_ctx


def _make_log_context() -> dict[str, str]:
    return {
        "db_path": ":memory:",
        "service": "flixpatrol",
        "endpoint": "/top10s",
        "operation": "test",
        "request_date": "2026-05-23",
        "key_fingerprint": "abc123",
    }


class TestFatalApiError(unittest.TestCase):
    def test_raised_on_401(self):
        from movietrace.sources.http import get_json, FatalApiError

        with patch(_URLOPEN_PATH) as mock_urlopen, patch(_SLEEP_PATH):
            mock_urlopen.side_effect = HTTPError(
                "https://example.com", 401, "Unauthorized", {}, None
            )
            with self.assertRaises(FatalApiError) as ctx:
                get_json("https://example.com/api")
            self.assertEqual(ctx.exception.status_code, 401)

    def test_raised_on_402(self):
        from movietrace.sources.http import get_json, FatalApiError

        with patch(_URLOPEN_PATH) as mock_urlopen, patch(_SLEEP_PATH):
            mock_urlopen.side_effect = HTTPError(
                "https://example.com", 402, "Payment Required", {}, None
            )
            with self.assertRaises(FatalApiError) as ctx:
                get_json("https://example.com/api")
            self.assertEqual(ctx.exception.status_code, 402)

    def test_raised_on_403(self):
        from movietrace.sources.http import get_json, FatalApiError

        with patch(_URLOPEN_PATH) as mock_urlopen, patch(_SLEEP_PATH):
            mock_urlopen.side_effect = HTTPError(
                "https://example.com", 403, "Forbidden", {}, None
            )
            with self.assertRaises(FatalApiError) as ctx:
                get_json("https://example.com/api")
            self.assertEqual(ctx.exception.status_code, 403)

    def test_not_raised_on_429(self):
        from movietrace.sources.http import get_json, FatalApiError

        with patch(_URLOPEN_PATH) as mock_urlopen, patch(_SLEEP_PATH):
            mock_urlopen.side_effect = HTTPError(
                "https://example.com", 429, "Too Many Requests", {}, None
            )
            with self.assertRaises(HTTPError):
                get_json("https://example.com/api")

    def test_not_raised_on_500(self):
        from movietrace.sources.http import get_json, FatalApiError

        with patch(_URLOPEN_PATH) as mock_urlopen, patch(_SLEEP_PATH):
            mock_urlopen.side_effect = HTTPError(
                "https://example.com", 500, "Internal Server Error", {}, None
            )
            with self.assertRaises(HTTPError):
                get_json("https://example.com/api")

    def test_not_raised_on_network_error(self):
        from movietrace.sources.http import get_json, FatalApiError

        with patch(_URLOPEN_PATH) as mock_urlopen, patch(_SLEEP_PATH):
            mock_urlopen.side_effect = TimeoutError("timed out")
            with self.assertRaises((TimeoutError, RuntimeError)):
                get_json("https://example.com/api")

    def test_fatal_api_error_message(self):
        from movietrace.sources.http import FatalApiError

        err = FatalApiError(401, "Bad credentials")
        self.assertIn("Bad credentials", str(err))
        self.assertEqual(err.status_code, 401)

    def test_fatal_api_error_default_message(self):
        from movietrace.sources.http import FatalApiError

        err = FatalApiError(403)
        self.assertIn("403", str(err))
        self.assertEqual(err.status_code, 403)

    def test_get_json_logs_single_usage_row(self):
        from movietrace.sources.http import get_json

        with patch(_URLOPEN_PATH, return_value=_make_mock_response()), \
             patch(_SLEEP_PATH), \
             patch(_LOG_API_CALL_PATH) as mock_log_api_call:
            result = get_json(
                "https://example.com/api",
                log_context=_make_log_context(),
            )

        self.assertEqual(result, {"results": [1, 2]})
        mock_log_api_call.assert_called_once()
        self.assertEqual(mock_log_api_call.call_args.kwargs["status"], "success")


if __name__ == "__main__":
    unittest.main()
