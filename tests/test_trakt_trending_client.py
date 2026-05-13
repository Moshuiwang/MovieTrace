import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


class TraktTrendingClientTest(unittest.TestCase):
    def setUp(self):
        from movietrace.sources.trakt import TraktTrendingClient
        self.client = TraktTrendingClient("fake-client-id")

    def test_fetch_shows_trending_flattens_nested_structure(self):
        sample = [
            {
                "watchers": 7810,
                "show": {
                    "ids": {"trakt": 139960, "tmdb": 76479, "imdb": "tt1190634"},
                    "title": "FROM",
                    "year": 2022,
                    "rating": 7.99,
                    "votes": 10182,
                },
            }
        ]
        with patch("movietrace.sources.trakt.get_json", return_value=sample):
            items = self.client.fetch_shows_trending()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["watchers"], 7810)
        self.assertEqual(items[0]["trakt_id"], 139960)
        self.assertEqual(items[0]["tmdb_id"], 76479)
        self.assertEqual(items[0]["imdb_id"], "tt1190634")
        self.assertEqual(items[0]["title"], "FROM")
        self.assertEqual(items[0]["media_type"], "show")

    def test_fetch_movies_trending_flattens_correctly(self):
        sample = [
            {
                "watchers": 3500,
                "movie": {
                    "ids": {"trakt": 500, "tmdb": 600, "imdb": "tt1234567"},
                    "title": "Test Movie",
                    "year": 2025,
                    "rating": 8.5,
                    "votes": 5000,
                },
            }
        ]
        with patch("movietrace.sources.trakt.get_json", return_value=sample):
            items = self.client.fetch_movies_trending()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["media_type"], "movie")
        self.assertEqual(items[0]["title"], "Test Movie")

    def test_missing_tmdb_id_returns_none_not_error(self):
        sample = [
            {
                "watchers": 100,
                "show": {
                    "ids": {"trakt": 999},
                    "title": "No TMDb Show",
                    "year": 2020,
                },
            }
        ]
        with patch("movietrace.sources.trakt.get_json", return_value=sample):
            items = self.client.fetch_shows_trending()
        self.assertEqual(len(items), 1)
        self.assertIsNone(items[0]["tmdb_id"])

    def test_trakt_client_uses_correct_headers(self):
        from movietrace.sources.trakt import TraktTrendingClient
        client = TraktTrendingClient("my-key")
        headers = client._headers()
        self.assertEqual(headers["trakt-api-key"], "my-key")
        self.assertEqual(headers["trakt-api-version"], "2")

    def test_normalize_trakt_trending_row(self):
        from movietrace.sources.trakt import normalize_trakt_trending_row
        item = {
            "watchers": 500, "trakt_id": 123, "tmdb_id": 456,
            "imdb_id": "tt1234567", "media_type": "show", "title": "Test",
            "year": 2025, "rating": 8.0, "votes": 1000,
        }
        row = normalize_trakt_trending_row(item, "shows/trending", "2026-05-13")
        self.assertIsNotNone(row)
        self.assertEqual(row["trakt_id"], 123)
        self.assertEqual(row["source_endpoint"], "shows/trending")
        self.assertEqual(row["snapshot_date"], "2026-05-13")

    def test_normalize_trakt_trending_row_no_trakt_id(self):
        from movietrace.sources.trakt import normalize_trakt_trending_row
        row = normalize_trakt_trending_row({"title": "No ID"}, "shows/trending", "2026-05-13")
        self.assertIsNone(row)


if __name__ == "__main__":
    unittest.main()
