import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


class TestHttpDefaultUA(unittest.TestCase):
    def test_get_json_default_ua_contains_mozilla(self):
        from movietrace.sources.http import get_json, DEFAULT_USER_AGENT

        self.assertIn("Mozilla", DEFAULT_USER_AGENT)
        self.assertIn("Firefox", DEFAULT_USER_AGENT)

    def test_get_json_caller_headers_can_override_ua(self):
        from movietrace.sources.http import get_json, DEFAULT_USER_AGENT

        custom_ua = "MovieTraceBot/0.1"
        with patch("movietrace.sources.http.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = b"{}"
            mock_resp.__enter__.return_value = mock_resp
            mock_urlopen.return_value = mock_resp

            get_json("https://example.com/api", headers={"User-Agent": custom_ua})

            call_args = mock_urlopen.call_args[0][0]
            self.assertEqual(call_args.get_header("User-agent"), custom_ua)

    def test_get_json_no_headers_uses_default_ua(self):
        from movietrace.sources.http import get_json, DEFAULT_USER_AGENT

        with patch("movietrace.sources.http.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = b"{}"
            mock_resp.__enter__.return_value = mock_resp
            mock_urlopen.return_value = mock_resp

            get_json("https://example.com/api")

            call_args = mock_urlopen.call_args[0][0]
            self.assertEqual(call_args.get_header("User-agent"), DEFAULT_USER_AGENT)


if __name__ == "__main__":
    unittest.main()
