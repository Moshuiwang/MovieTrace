import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


class TraktTrendingPipelineTest(unittest.TestCase):
    def setUp(self):
        from movietrace.db.schema import initialize_database, connect_database
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / "test_trakt_trending.db"
        initialize_database(self.db_path)
        self.conn = connect_database(self.db_path)

    def tearDown(self):
        self.conn.close()
        self.tmpdir.cleanup()

    def _mock_client(self):
        mock = unittest.mock.MagicMock()
        mock.fetch_shows_trending.return_value = [
            {"watchers": 7810, "trakt_id": 139960, "tmdb_id": 76479,
             "imdb_id": "tt1190634", "media_type": "show", "title": "FROM",
             "year": 2022, "rating": 7.99, "votes": 10182,
             "raw_payload": {}},
            {"watchers": 500, "trakt_id": 200, "tmdb_id": None,
             "imdb_id": None, "media_type": "show", "title": "No TMDb Show",
             "year": 2023, "rating": None, "votes": None,
             "raw_payload": {}},
        ]
        mock.fetch_movies_trending.return_value = [
            {"watchers": 3500, "trakt_id": 300, "tmdb_id": 500,
             "imdb_id": "tt9876543", "media_type": "movie", "title": "Hot Movie",
             "year": 2025, "rating": 8.5, "votes": 5000,
             "raw_payload": {}},
        ]
        return mock

    def _feed_data(self):
        from movietrace.pipeline.trakt_trending import fetch_and_store_trakt_trending
        with patch("movietrace.pipeline.trakt_trending.TraktTrendingClient", return_value=self._mock_client()):
            with patch("movietrace.pipeline.trakt_trending.time.sleep", return_value=None):
                return fetch_and_store_trakt_trending(
                    db_path=str(self.db_path),
                    client_id="fake-id",
                    snapshot_date="2026-05-13",
                )

    def test_writes_correct_count(self):
        result = self._feed_data()
        self.assertEqual(result["inserted"], 3)

    def test_duplicate_execution_inserts_zero(self):
        self._feed_data()
        result2 = self._feed_data()
        self.assertEqual(result2["inserted"], 0)

    def test_shows_and_movies_both_inserted(self):
        self._feed_data()
        shows = self.conn.execute(
            "select count(*) from trakt_trending where media_type='show' and snapshot_date='2026-05-13'"
        ).fetchone()[0]
        movies = self.conn.execute(
            "select count(*) from trakt_trending where media_type='movie' and snapshot_date='2026-05-13'"
        ).fetchone()[0]
        self.assertEqual(shows, 2)
        self.assertEqual(movies, 1)

    def test_missing_tmdb_id_inserted_without_error(self):
        self._feed_data()
        row = self.conn.execute(
            "select trakt_id, tmdb_id from trakt_trending where trakt_id=200"
        ).fetchone()
        self.assertEqual(row[0], 200)
        self.assertIsNone(row[1])


if __name__ == "__main__":
    unittest.main()
