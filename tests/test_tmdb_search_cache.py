"""P1.44: Tests for TmdbSearchClient search_tv / search_movie api_cache integration (72h TTL)."""
from __future__ import annotations

import json
import sqlite3
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

_FAKE_TV_PAYLOAD = {
    "results": [
        {
            "id": 1396,
            "name": "Breaking Bad",
            "first_air_date": "2008-01-20",
            "popularity": 200.0,
        }
    ]
}

_FAKE_MOVIE_PAYLOAD = {
    "results": [
        {
            "id": 438631,
            "title": "Dune",
            "release_date": "2021-09-15",
            "popularity": 150.0,
        }
    ]
}


def _make_conn() -> sqlite3.Connection:
    """Create in-memory SQLite with api_cache and api_usage_log tables."""
    conn = sqlite3.connect(":memory:")
    conn.execute(
        """create table api_cache (
               id integer primary key,
               source text not null,
               cache_key text not null,
               response_json text,
               fetched_at datetime default (strftime('%Y-%m-%d %H:%M:%S', 'now')),
               expires_at text,
               unique(source, cache_key)
           )"""
    )
    conn.execute(
        """create table api_usage_log (
               id integer primary key,
               service text,
               endpoint text,
               operation text,
               request_date text,
               status text,
               http_status integer,
               cache_status text,
               quota_error integer default 0,
               rate_limited integer default 0,
               duration_ms integer,
               item_count integer,
               error_code text,
               error_message text,
               key_fingerprint text,
               metadata_json text,
               created_at datetime default current_timestamp
           )"""
    )
    conn.commit()
    return conn


class TestSearchTvWritesCacheOnFirstCall(unittest.TestCase):
    """test_search_tv_writes_cache_on_first_call"""

    def test_search_tv_writes_cache_on_first_call(self):
        from movietrace.sources.tmdb import TmdbSearchClient

        conn = _make_conn()
        client = TmdbSearchClient("fake-token", conn=conn)

        with patch("movietrace.sources.tmdb.get_json", return_value=_FAKE_TV_PAYLOAD):
            results = client.search_tv("Breaking Bad")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, "Breaking Bad")

        row = conn.execute(
            "select cache_key from api_cache where source = 'tmdb' and cache_key = ?",
            ("tmdb:search:tv:breaking bad",),
        ).fetchone()
        self.assertIsNotNone(row, "api_cache should contain tmdb:search:tv:breaking bad")


class TestSearchTvCacheHitSkipsNetwork(unittest.TestCase):
    """test_search_tv_cache_hit_skips_network"""

    def test_search_tv_cache_hit_skips_network(self):
        from movietrace.sources.tmdb import TmdbSearchClient

        conn = _make_conn()
        conn.execute(
            """insert into api_cache (source, cache_key, response_json, fetched_at)
               values ('tmdb', 'tmdb:search:tv:breaking bad', ?, strftime('%Y-%m-%d %H:%M:%S', 'now'))""",
            (json.dumps(_FAKE_TV_PAYLOAD),),
        )
        conn.commit()

        client = TmdbSearchClient("fake-token", conn=conn)

        with patch("movietrace.sources.tmdb.get_json") as mock_get:
            results = client.search_tv("Breaking Bad")
            self.assertEqual(mock_get.call_count, 0, "get_json must NOT be called on cache hit")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, "Breaking Bad")
        self.assertEqual(results[0].media_type, "tv")


class TestSearchMovieCacheIndependentOfTv(unittest.TestCase):
    """test_search_movie_cache_independent_of_tv"""

    def test_search_movie_cache_independent_of_tv(self):
        from movietrace.sources.tmdb import TmdbSearchClient

        conn = _make_conn()
        # Pre-seed TV cache for "dune" — must NOT satisfy movie query
        conn.execute(
            """insert into api_cache (source, cache_key, response_json, fetched_at)
               values ('tmdb', 'tmdb:search:tv:dune', '{"results":[]}',
                       strftime('%Y-%m-%d %H:%M:%S', 'now'))""",
        )
        conn.commit()

        client = TmdbSearchClient("fake-token", conn=conn)

        with patch("movietrace.sources.tmdb.get_json", return_value=_FAKE_MOVIE_PAYLOAD) as mock_get:
            results = client.search_movie("Dune")
            self.assertEqual(mock_get.call_count, 1, "get_json MUST be called (TV cache != movie cache)")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, "Dune")


class TestSearchCacheExpiredRefetches(unittest.TestCase):
    """test_search_cache_expired_refetches"""

    def test_search_cache_expired_refetches(self):
        from movietrace.sources.tmdb import TmdbSearchClient

        conn = _make_conn()

        # Insert cache entry with fetched_at 73 hours ago (expired for 72h TTL)
        stale_ts = (datetime.now(timezone.utc) - timedelta(hours=73)).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        stale_payload = {"results": [{"id": 999, "name": "Stale Result", "first_air_date": "2000-01-01", "popularity": 1.0}]}
        conn.execute(
            """insert into api_cache (source, cache_key, response_json, fetched_at)
               values ('tmdb', 'tmdb:search:tv:breaking bad', ?, ?)""",
            (json.dumps(stale_payload), stale_ts),
        )
        conn.commit()

        client = TmdbSearchClient("fake-token", conn=conn)
        fresh_payload = _FAKE_TV_PAYLOAD

        with patch("movietrace.sources.tmdb.get_json", return_value=fresh_payload) as mock_get:
            results = client.search_tv("Breaking Bad")
            self.assertEqual(mock_get.call_count, 1, "get_json must be called once for expired cache")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, "Breaking Bad")

        # Cache should now be refreshed
        row = conn.execute(
            "select response_json from api_cache where source = 'tmdb' and cache_key = 'tmdb:search:tv:breaking bad'",
        ).fetchone()
        self.assertIsNotNone(row)
        stored = json.loads(row[0])
        self.assertEqual(stored, fresh_payload)


class TestSearchCacheHitLogsApiUsage(unittest.TestCase):
    """Cache hit must write a cache_hit row to api_usage_log when db_path + request_date are set."""

    def test_cache_hit_writes_usage_log(self):
        from movietrace.sources.tmdb import TmdbSearchClient

        conn = _make_conn()
        conn.execute(
            """insert into api_cache (source, cache_key, response_json, fetched_at)
               values ('tmdb', 'tmdb:search:tv:breaking bad', ?, strftime('%Y-%m-%d %H:%M:%S', 'now'))""",
            (json.dumps(_FAKE_TV_PAYLOAD),),
        )
        conn.commit()

        # Patch log_api_call to intercept without actually writing to a db file
        with patch("movietrace.sources.tmdb.log_api_call") as mock_log:
            client = TmdbSearchClient(
                "fake-token",
                db_path="/tmp/fake.db",
                request_date="2026-05-22",
                conn=conn,
            )
            with patch("movietrace.sources.tmdb.get_json") as mock_get:
                client.search_tv("Breaking Bad")
                self.assertEqual(mock_get.call_count, 0)

            mock_log.assert_called_once()
            call_kwargs = mock_log.call_args[1]
            self.assertEqual(call_kwargs["status"], "cache_hit")
            self.assertEqual(call_kwargs["endpoint"], "/search/tv")


if __name__ == "__main__":
    unittest.main()
