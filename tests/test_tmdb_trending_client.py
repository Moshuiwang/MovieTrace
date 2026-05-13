import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


class TmdbTrendingClientTest(unittest.TestCase):
    def setUp(self):
        from movietrace.sources.tmdb import TmdbTrendingClient
        self.client = TmdbTrendingClient("fake-token")

    def _mock_response(self, data, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = __import__("json").dumps(data).encode()
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

    def test_fetch_trending_all_day_parses_fields(self):
        sample = {
            "results": [
                {
                    "id": 76479, "media_type": "tv", "name": "The Boys",
                    "original_name": "The Boys", "first_air_date": "2019-07-26",
                    "original_language": "en", "popularity": 569.2,
                    "vote_average": 8.45, "vote_count": 12247,
                },
                {
                    "id": 603692, "media_type": "movie", "title": "John Wick 4",
                    "original_title": "John Wick: Chapter 4",
                    "release_date": "2023-03-22",
                    "original_language": "en", "popularity": 310.5,
                    "vote_average": 7.6, "vote_count": 5500,
                },
            ]
        }
        with patch("movietrace.sources.tmdb.get_json", return_value=sample):
            items = self.client.fetch_trending_all_day(page=1)
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["name"], "The Boys")
        self.assertEqual(items[0]["media_type"], "tv")
        self.assertEqual(items[1]["title"], "John Wick 4")

    def test_fetch_tv_popular_adds_media_type_tv(self):
        sample = {
            "results": [
                {"id": 100, "name": "Show X", "popularity": 200.0},
            ]
        }
        with patch("movietrace.sources.tmdb.get_json", return_value=sample):
            items = self.client.fetch_tv_popular(page=1)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["media_type"], "tv")

    def test_fetch_movie_popular_adds_media_type_movie(self):
        sample = {
            "results": [
                {"id": 200, "title": "Movie Y", "popularity": 150.0},
            ]
        }
        with patch("movietrace.sources.tmdb.get_json", return_value=sample):
            items = self.client.fetch_movie_popular(page=1)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["media_type"], "movie")

    def test_page_parameter_passed_correctly(self):
        with patch("movietrace.sources.tmdb.get_json") as mock_get:
            mock_get.return_value = {"results": []}
            self.client.fetch_tv_popular(page=3)
            call_kwargs = mock_get.call_args[1]
            self.assertEqual(call_kwargs["params"]["page"], "3")

    def test_error_response_returns_empty_list(self):
        with patch("movietrace.sources.tmdb.get_json", return_value={"error": "not found"}):
            items = self.client.fetch_trending_all_day(page=1)
        self.assertEqual(items, [])

    def test_normalize_tmdb_trending_row_movie(self):
        from movietrace.sources.tmdb import normalize_tmdb_trending_row
        item = {
            "id": 603692, "media_type": "movie", "title": "JW4",
            "release_date": "2023-03-22", "popularity": 310.5,
            "vote_average": 7.6, "vote_count": 5500,
        }
        row = normalize_tmdb_trending_row(item, "movie/popular", 2, "2026-05-13")
        self.assertIsNotNone(row)
        self.assertEqual(row["tmdb_id"], 603692)
        self.assertEqual(row["media_type"], "movie")
        self.assertEqual(row["source_endpoint"], "movie/popular")
        self.assertEqual(row["source_page"], 2)
        self.assertEqual(row["snapshot_date"], "2026-05-13")
        self.assertEqual(row["popularity"], 310.5)
        self.assertEqual(row["vote_average"], 7.6)

    def test_normalize_tmdb_trending_row_tv(self):
        from movietrace.sources.tmdb import normalize_tmdb_trending_row
        item = {
            "id": 76479, "media_type": "tv", "name": "The Boys",
            "first_air_date": "2019-07-26", "popularity": 569.2,
        }
        row = normalize_tmdb_trending_row(item, "trending/day", 1, "2026-05-13")
        self.assertIsNotNone(row)
        self.assertEqual(row["title"], "The Boys")
        self.assertEqual(row["release_date"], "2019-07-26")

    def test_normalize_tmdb_trending_row_no_id_returns_none(self):
        from movietrace.sources.tmdb import normalize_tmdb_trending_row
        row = normalize_tmdb_trending_row({"title": "No ID"}, "trending/day", 1, "2026-05-13")
        self.assertIsNone(row)


if __name__ == "__main__":
    unittest.main()
