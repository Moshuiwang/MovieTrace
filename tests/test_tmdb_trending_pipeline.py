import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


class TmdbTrendingPipelineTest(unittest.TestCase):
    def setUp(self):
        from movietrace.db.schema import initialize_database, connect_database
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / "test_tmdb_trending.db"
        initialize_database(self.db_path)
        self.conn = connect_database(self.db_path)

    def tearDown(self):
        self.conn.close()
        self.tmpdir.cleanup()

    def _mock_client(self):
        """Return a mock TmdbTrendingClient that returns canned data."""
        mock = unittest.mock.MagicMock()
        mock.fetch_trending_all_day.return_value = [
            {"id": 76479, "media_type": "tv", "name": "The Boys",
             "first_air_date": "2019-07-26", "popularity": 569.2,
             "vote_average": 8.45, "vote_count": 12247},
            {"id": 100, "media_type": "movie", "title": "Movie A",
             "release_date": "2025-01-15", "popularity": 200.0,
             "vote_average": 7.0, "vote_count": 1000},
        ]
        mock.fetch_tv_popular.return_value = [
            {"id": 76479, "media_type": "tv", "name": "The Boys",
             "first_air_date": "2019-07-26", "popularity": 569.2,
             "vote_average": 8.45, "vote_count": 12247},
            {"id": 200, "media_type": "tv", "name": "TV Show B",
             "first_air_date": "2024-06-01", "popularity": 100.0,
             "vote_average": 8.0, "vote_count": 500},
        ]
        mock.fetch_movie_popular.return_value = [
            {"id": 300, "media_type": "movie", "title": "Movie C",
             "release_date": "2025-03-10", "popularity": 150.0,
             "vote_average": 6.5, "vote_count": 300},
        ]
        return mock

    def _feed_data(self):
        from movietrace.pipeline.tmdb_trending import fetch_and_store_tmdb_trending
        with patch("movietrace.pipeline.tmdb_trending.TmdbTrendingClient", return_value=self._mock_client()):
            with patch("movietrace.pipeline.tmdb_trending.time.sleep", return_value=None):
                return fetch_and_store_tmdb_trending(
                    db_path=str(self.db_path),
                    bearer_token="fake-token",
                    snapshot_date="2026-05-13",
                )

    def test_writes_correct_count(self):
        result = self._feed_data()
        self.assertGreaterEqual(result["inserted"], 3)

    def test_duplicate_execution_inserts_zero(self):
        self._feed_data()
        result2 = self._feed_data()
        self.assertEqual(result2["inserted"], 0)

    def test_movie_and_tv_both_inserted(self):
        self._feed_data()
        tv_count = self.conn.execute(
            "select count(*) from tmdb_trending where media_type='tv' and snapshot_date='2026-05-13'"
        ).fetchone()[0]
        movie_count = self.conn.execute(
            "select count(*) from tmdb_trending where media_type='movie' and snapshot_date='2026-05-13'"
        ).fetchone()[0]
        self.assertGreaterEqual(tv_count, 1)
        self.assertGreaterEqual(movie_count, 1)

    def test_endpoints_recorded_correctly(self):
        self._feed_data()
        endpoints = self.conn.execute(
            "select distinct source_endpoint from tmdb_trending where snapshot_date='2026-05-13'"
        ).fetchall()
        names = [r[0] for r in endpoints]
        self.assertIn("trending/day", names)

    def test_default_pages_per_endpoint_is_one(self):
        mock = self._mock_client()
        with patch("movietrace.pipeline.tmdb_trending.TmdbTrendingClient", return_value=mock):
            with patch("movietrace.pipeline.tmdb_trending.time.sleep", return_value=None):
                from movietrace.pipeline.tmdb_trending import fetch_and_store_tmdb_trending
                fetch_and_store_tmdb_trending(
                    db_path=str(self.db_path),
                    bearer_token="fake-token",
                    snapshot_date="2026-05-13",
                )
        self.assertEqual(mock.fetch_trending_all_day.call_count, 1)
        self.assertEqual(mock.fetch_tv_popular.call_count, 1)
        self.assertEqual(mock.fetch_movie_popular.call_count, 1)

    def test_explicit_pages_three_calls_three_pages(self):
        mock = self._mock_client()
        with patch("movietrace.pipeline.tmdb_trending.TmdbTrendingClient", return_value=mock):
            with patch("movietrace.pipeline.tmdb_trending.time.sleep", return_value=None):
                from movietrace.pipeline.tmdb_trending import fetch_and_store_tmdb_trending
                fetch_and_store_tmdb_trending(
                    db_path=str(self.db_path),
                    bearer_token="fake-token",
                    snapshot_date="2026-05-13",
                    pages_per_endpoint=3,
                )
        self.assertEqual(mock.fetch_trending_all_day.call_count, 3)
        self.assertEqual(mock.fetch_tv_popular.call_count, 3)
        self.assertEqual(mock.fetch_movie_popular.call_count, 3)

    def test_single_page_failure_does_not_block_others(self):
        mock = self._mock_client()
        mock.fetch_tv_popular.side_effect = Exception("API error")

        with patch("movietrace.pipeline.tmdb_trending.TmdbTrendingClient", return_value=mock):
            with patch("movietrace.pipeline.tmdb_trending.time.sleep", return_value=None):
                from movietrace.pipeline.tmdb_trending import fetch_and_store_tmdb_trending
                result = fetch_and_store_tmdb_trending(
                    db_path=str(self.db_path),
                    bearer_token="fake-token",
                    snapshot_date="2026-05-13",
                )
        self.assertGreater(result["errors"], 0)
        self.assertGreater(result["inserted"], 0)


if __name__ == "__main__":
    unittest.main()
