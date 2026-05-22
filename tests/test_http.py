from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

# urlopen is now called from _http_policy; patch there so mock takes effect
_URLOPEN_PATH = "movietrace.sources._http_policy.urlopen"
_SLEEP_PATH = "movietrace.sources._http_policy.time.sleep"


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


if __name__ == "__main__":
    unittest.main()
