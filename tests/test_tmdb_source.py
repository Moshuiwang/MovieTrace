import json
import sqlite3
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


class TmdbDetailClientTest(unittest.TestCase):
    """Tests for TmdbDetailClient.get_tv_season_details method."""

    def setUp(self):
        from movietrace.sources.tmdb import TmdbDetailClient
        self.client = TmdbDetailClient("fake-token")

    def test_get_tv_season_details_basic(self):
        """Test basic season detail retrieval with mock response."""
        fake_season_data = {
            "id": 3620,
            "season_number": 5,
            "episode_count": 10,
            "episodes": [
                {"id": 123, "episode_number": 1, "name": "Pilot"},
                {"id": 124, "episode_number": 2, "name": "Second"},
            ],
            "name": "Season 5",
        }
        with patch("movietrace.sources.tmdb.get_json", return_value=fake_season_data):
            result = self.client.get_tv_season_details("1234", 5)
            self.assertEqual(result, fake_season_data)
            self.assertEqual(result.get("episode_count"), 10)
            self.assertEqual(len(result.get("episodes", [])), 2)

    def test_get_tv_season_details_with_int_tv_id(self):
        """Test that integer tv_id is handled correctly."""
        fake_season_data = {"id": 3620, "season_number": 5, "episode_count": 8}
        with patch("movietrace.sources.tmdb.get_json", return_value=fake_season_data):
            result = self.client.get_tv_season_details(1234, 5)
            self.assertEqual(result, fake_season_data)

    def test_get_tv_season_details_returns_empty_on_non_dict(self):
        """Test that non-dict responses return empty dict."""
        with patch("movietrace.sources.tmdb.get_json", return_value="not a dict"):
            result = self.client.get_tv_season_details("1234", 5)
            self.assertEqual(result, {})

    def test_get_tv_season_details_returns_empty_on_none(self):
        """Test that None response returns empty dict."""
        with patch("movietrace.sources.tmdb.get_json", return_value=None):
            result = self.client.get_tv_season_details("1234", 5)
            self.assertEqual(result, {})

    def test_get_tv_season_details_returns_empty_on_list(self):
        """Test that list response returns empty dict."""
        with patch("movietrace.sources.tmdb.get_json", return_value=[]):
            result = self.client.get_tv_season_details("1234", 5)
            self.assertEqual(result, {})

    def test_get_tv_season_details_calls_correct_url(self):
        """Test that correct URL is constructed."""
        fake_season_data = {"id": 3620, "season_number": 2, "episode_count": 12}
        with patch("movietrace.sources.tmdb.get_json", return_value=fake_season_data) as mock_get:
            self.client.get_tv_season_details("999", 2)
            # Verify get_json was called with correct URL
            call_args = mock_get.call_args
            self.assertIn("/tv/999/season/2", call_args[0][0])

    def test_get_tv_season_details_passes_language_param(self):
        """Test that language parameter is set correctly."""
        fake_season_data = {"id": 3620}
        with patch("movietrace.sources.tmdb.get_json", return_value=fake_season_data) as mock_get:
            self.client.get_tv_season_details("1234", 5)
            call_args = mock_get.call_args
            self.assertEqual(call_args[1]["params"].get("language"), "en-US")

    def test_get_tv_season_details_includes_auth_header(self):
        """Test that Bearer token is included in headers."""
        fake_season_data = {"id": 3620}
        with patch("movietrace.sources.tmdb.get_json", return_value=fake_season_data) as mock_get:
            self.client.get_tv_season_details("1234", 5)
            call_args = mock_get.call_args
            headers = call_args[1]["headers"]
            self.assertIn("Authorization", headers)
            self.assertIn("Bearer", headers["Authorization"])


class SeasonDetailCacheTest(unittest.TestCase):
    """Tests for season detail cache helpers."""

    def setUp(self):
        from movietrace.pipeline.tmdb_detail_cache import season_detail_cache_key
        self.season_detail_cache_key = season_detail_cache_key

    def test_season_detail_cache_key_format(self):
        """Test cache key generation."""
        key = self.season_detail_cache_key(123, 5)
        self.assertEqual(key, "tmdb:detail:123:season:5")

    def test_season_detail_cache_key_with_str_tv_id(self):
        """Test cache key with string TV ID."""
        key = self.season_detail_cache_key("456", 2)
        self.assertEqual(key, "tmdb:detail:456:season:2")

    def test_season_detail_cache_key_with_special_season_numbers(self):
        """Test cache key with special season numbers (0, large numbers)."""
        key0 = self.season_detail_cache_key(789, 0)
        key_large = self.season_detail_cache_key(789, 100)
        self.assertEqual(key0, "tmdb:detail:789:season:0")
        self.assertEqual(key_large, "tmdb:detail:789:season:100")


class SeasonDetailCacheIntegrationTest(unittest.TestCase):
    """Integration tests for season detail cache with database."""

    def setUp(self):
        # Create in-memory SQLite database with api_cache table
        self.conn = sqlite3.connect(":memory:")
        self.conn.execute("""
            create table api_cache (
                id integer primary key,
                source text not null,
                cache_key text not null,
                response_json text,
                fetched_at datetime default current_timestamp,
                unique(source, cache_key)
            )
        """)
        self.conn.commit()

    def tearDown(self):
        self.conn.close()

    def test_season_detail_cache_miss_calls_api(self):
        """Test that cache miss triggers API call."""
        from movietrace.pipeline.tmdb_detail_cache import get_tmdb_season_detail_with_cache
        from movietrace.sources.tmdb import TmdbDetailClient

        fake_season_data = {"id": 3620, "season_number": 5, "episode_count": 10}
        client = MagicMock(spec=TmdbDetailClient)
        client.get_tv_season_details.return_value = fake_season_data

        with patch("movietrace.pipeline.tmdb_detail_cache.TmdbSeasonDetailGetter", client):
            result, was_cached = get_tmdb_season_detail_with_cache(
                self.conn, client, "1234", 5
            )
            self.assertEqual(result, fake_season_data)
            self.assertFalse(was_cached)
            # Verify API was called
            client.get_tv_season_details.assert_called_once_with("1234", 5)

    def test_season_detail_cache_hit_skips_api(self):
        """Test that cache hit skips API call."""
        from movietrace.pipeline.tmdb_detail_cache import (
            get_tmdb_season_detail_with_cache,
            write_tmdb_season_detail_cache,
        )

        fake_season_data = {"id": 3620, "season_number": 5, "episode_count": 10}
        # Pre-populate cache
        write_tmdb_season_detail_cache(self.conn, "1234", 5, fake_season_data)

        client = MagicMock()
        client.get_tv_season_details.return_value = {}  # Should not be called

        result, was_cached = get_tmdb_season_detail_with_cache(
            self.conn, client, "1234", 5
        )
        self.assertEqual(result, fake_season_data)
        self.assertTrue(was_cached)
        # Verify API was NOT called
        client.get_tv_season_details.assert_not_called()

    def test_season_detail_cache_ttl_expired(self):
        """Test that expired cache is bypassed and API is called."""
        from movietrace.pipeline.tmdb_detail_cache import (
            get_tmdb_season_detail_with_cache,
            season_detail_cache_key,
        )

        # Insert stale cache entry (25 hours ago)
        stale_data = {"id": 3620, "season_number": 5, "episode_count": 8}
        stale_timestamp = (datetime.now(timezone.utc) - timedelta(hours=25)).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        self.conn.execute(
            """insert into api_cache (source, cache_key, response_json, fetched_at)
               values (?, ?, ?, ?)""",
            ("tmdb", season_detail_cache_key("1234", 5), json.dumps(stale_data), stale_timestamp),
        )
        self.conn.commit()

        fresh_data = {"id": 3620, "season_number": 5, "episode_count": 10}
        client = MagicMock()
        client.get_tv_season_details.return_value = fresh_data

        # With default 24h TTL, should trigger API call
        result, was_cached = get_tmdb_season_detail_with_cache(
            self.conn, client, "1234", 5, ttl_hours=24
        )
        self.assertEqual(result, fresh_data)
        self.assertFalse(was_cached)
        # Verify API was called
        client.get_tv_season_details.assert_called_once_with("1234", 5)

    def test_season_detail_write_cache_stores_json(self):
        """Test that write_tmdb_season_detail_cache stores data correctly."""
        from movietrace.pipeline.tmdb_detail_cache import (
            write_tmdb_season_detail_cache,
            season_detail_cache_key,
        )

        data = {"id": 3620, "season_number": 5, "episode_count": 10, "episodes": []}
        write_tmdb_season_detail_cache(self.conn, "1234", 5, data)

        # Verify stored data
        row = self.conn.execute(
            "select response_json from api_cache where cache_key = ?",
            (season_detail_cache_key("1234", 5),),
        ).fetchone()
        self.assertIsNotNone(row)
        stored_data = json.loads(row[0])
        self.assertEqual(stored_data, data)

    def test_season_detail_read_cache_handles_invalid_json(self):
        """Test that read_tmdb_season_detail_cache handles corrupted JSON."""
        from movietrace.pipeline.tmdb_detail_cache import (
            read_tmdb_season_detail_cache,
            season_detail_cache_key,
        )

        # Insert corrupted JSON
        self.conn.execute(
            """insert into api_cache (source, cache_key, response_json)
               values (?, ?, ?)""",
            ("tmdb", season_detail_cache_key("1234", 5), "not valid json {"),
        )
        self.conn.commit()

        result = read_tmdb_season_detail_cache(self.conn, "1234", 5)
        self.assertIsNone(result)

    def test_season_detail_read_cache_handles_non_dict_json(self):
        """Test that read_tmdb_season_detail_cache rejects non-dict JSON."""
        from movietrace.pipeline.tmdb_detail_cache import (
            read_tmdb_season_detail_cache,
            season_detail_cache_key,
        )

        # Insert list instead of dict
        self.conn.execute(
            """insert into api_cache (source, cache_key, response_json)
               values (?, ?, ?)""",
            ("tmdb", season_detail_cache_key("1234", 5), json.dumps(["a", "b"])),
        )
        self.conn.commit()

        result = read_tmdb_season_detail_cache(self.conn, "1234", 5)
        self.assertIsNone(result)

    def test_season_detail_get_with_cache_handles_empty_api_response(self):
        """Test that empty API response returns None."""
        from movietrace.pipeline.tmdb_detail_cache import get_tmdb_season_detail_with_cache

        client = MagicMock()
        client.get_tv_season_details.return_value = {}  # Empty dict

        result, was_cached = get_tmdb_season_detail_with_cache(
            self.conn, client, "1234", 5
        )
        self.assertIsNone(result)
        self.assertFalse(was_cached)

    def test_season_detail_get_with_cache_handles_non_dict_api_response(self):
        """Test that non-dict API response returns None."""
        from movietrace.pipeline.tmdb_detail_cache import get_tmdb_season_detail_with_cache

        client = MagicMock()
        client.get_tv_season_details.return_value = "invalid"  # String, not dict

        result, was_cached = get_tmdb_season_detail_with_cache(
            self.conn, client, "1234", 5
        )
        self.assertIsNone(result)
        self.assertFalse(was_cached)


if __name__ == "__main__":
    unittest.main()
