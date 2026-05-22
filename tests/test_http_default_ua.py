import sys
import unittest
from http.client import HTTPMessage
from pathlib import Path
from unittest.mock import patch, MagicMock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

# urlopen is now called from _http_policy; patch there so mock takes effect
_URLOPEN_PATH = "movietrace.sources._http_policy.urlopen"


def _make_mock_response(body_bytes: bytes = b"{}") -> MagicMock:
    """Build a mock urlopen context manager response."""
    headers = HTTPMessage()
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = body_bytes
    mock_resp.headers = headers
    mock_ctx = MagicMock()
    mock_ctx.__enter__ = MagicMock(return_value=mock_resp)
    mock_ctx.__exit__ = MagicMock(return_value=False)
    return mock_ctx


class TestHttpDefaultUA(unittest.TestCase):
    def test_get_json_default_ua_contains_mozilla(self):
        from movietrace.sources.http import get_json, DEFAULT_USER_AGENT

        self.assertIn("Mozilla", DEFAULT_USER_AGENT)
        self.assertIn("Firefox", DEFAULT_USER_AGENT)

    def test_get_json_caller_headers_can_override_ua(self):
        from movietrace.sources.http import get_json, DEFAULT_USER_AGENT

        custom_ua = "MovieTraceBot/0.1"
        with patch(_URLOPEN_PATH) as mock_urlopen:
            mock_urlopen.return_value = _make_mock_response()

            get_json("https://example.com/api", headers={"User-Agent": custom_ua})

            call_args = mock_urlopen.call_args[0][0]
            self.assertEqual(call_args.get_header("User-agent"), custom_ua)

    def test_get_json_no_headers_uses_default_ua(self):
        from movietrace.sources.http import get_json, DEFAULT_USER_AGENT

        with patch(_URLOPEN_PATH) as mock_urlopen:
            mock_urlopen.return_value = _make_mock_response()

            get_json("https://example.com/api")

            call_args = mock_urlopen.call_args[0][0]
            self.assertEqual(call_args.get_header("User-agent"), DEFAULT_USER_AGENT)


if __name__ == "__main__":
    unittest.main()
