"""Tests for HTTP get_json() gzip decompression support (P1.35)."""
from __future__ import annotations

import gzip
import json
import sys
import unittest
from http.client import HTTPMessage
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def _make_mock_response(body_bytes: bytes, content_encoding: str | None = None) -> MagicMock:
    """Build a mock urlopen context manager response."""
    headers = HTTPMessage()
    if content_encoding:
        headers["Content-Encoding"] = content_encoding

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = body_bytes
    mock_resp.headers = headers

    # Support `with urlopen(...) as response:` pattern
    mock_ctx = MagicMock()
    mock_ctx.__enter__ = MagicMock(return_value=mock_resp)
    mock_ctx.__exit__ = MagicMock(return_value=False)
    return mock_ctx


class TestGetJsonGzip(unittest.TestCase):
    def test_gzip_response_is_correctly_decompressed(self):
        """get_json() must decompress a gzip-encoded response and return parsed JSON."""
        from movietrace.sources.http import get_json

        payload = {"results": [{"id": 1, "title": "Inception"}]}
        compressed = gzip.compress(json.dumps(payload).encode("utf-8"))

        mock_ctx = _make_mock_response(compressed, content_encoding="gzip")

        with patch("movietrace.sources.http.urlopen", return_value=mock_ctx):
            result = get_json("https://api.tmdb.org/3/trending/movie/week")

        self.assertEqual(result, payload)
        self.assertEqual(result["results"][0]["title"], "Inception")

    def test_plain_response_is_unaffected(self):
        """get_json() must handle a plain (non-compressed) response without change."""
        from movietrace.sources.http import get_json

        payload = {"page": 1, "total_results": 42}
        body_bytes = json.dumps(payload).encode("utf-8")

        mock_ctx = _make_mock_response(body_bytes, content_encoding=None)

        with patch("movietrace.sources.http.urlopen", return_value=mock_ctx):
            result = get_json("https://api.tmdb.org/3/movie/popular")

        self.assertEqual(result, payload)
        self.assertEqual(result["total_results"], 42)


if __name__ == "__main__":
    unittest.main()
