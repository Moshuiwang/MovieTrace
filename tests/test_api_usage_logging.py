"""Tests for API usage logging helper and key security."""

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


class FingerprintKeyTest(unittest.TestCase):
    def test_fingerprint_is_12_chars(self):
        from movietrace.logging.api_usage import fingerprint_key

        fp = fingerprint_key("my-secret-api-key-12345")
        self.assertEqual(len(fp), 12)

    def test_fingerprint_is_hex(self):
        from movietrace.logging.api_usage import fingerprint_key

        fp = fingerprint_key("test-key")
        self.assertTrue(all(c in "0123456789abcdef" for c in fp))

    def test_fingerprint_does_not_contain_original_key(self):
        from movietrace.logging.api_usage import fingerprint_key

        key = "super-secret-tmdb-token-abc123"
        fp = fingerprint_key(key)
        self.assertNotIn("super-secret", fp)
        self.assertNotIn("abc123", fp)
        self.assertNotIn(key, fp)

    def test_fingerprint_deterministic(self):
        from movietrace.logging.api_usage import fingerprint_key

        key = "deterministic-test"
        self.assertEqual(fingerprint_key(key), fingerprint_key(key))

    def test_fingerprint_empty_key(self):
        from movietrace.logging.api_usage import fingerprint_key

        self.assertEqual(fingerprint_key(""), "")


class LogApiCallTest(unittest.TestCase):
    def setUp(self):
        from movietrace.db.schema import initialize_database, connect_database

        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.tmpdir.name) / "test_usage.db")
        initialize_database(self.db_path)
        self.conn = connect_database(self.db_path)

    def tearDown(self):
        self.conn.close()
        self.tmpdir.cleanup()

    def _count_logs(self) -> int:
        return self.conn.execute("select count(*) from api_usage_log").fetchone()[0]

    def test_log_success(self):
        from movietrace.logging.api_usage import log_api_call

        log_api_call(
            db_path=self.db_path,
            service="tmdb",
            endpoint="/test",
            operation="test.log_success",
            request_date="2026-05-14",
            status="success",
            http_status=200,
            duration_ms=100,
            item_count=20,
            key_fingerprint="abc123",
        )

        row = self.conn.execute(
            "select service, endpoint, operation, status, http_status, duration_ms, item_count, key_fingerprint from api_usage_log"
        ).fetchone()
        self.assertEqual(row[0], "tmdb")
        self.assertEqual(row[1], "/test")
        self.assertEqual(row[2], "test.log_success")
        self.assertEqual(row[3], "success")
        self.assertEqual(row[4], 200)
        self.assertEqual(row[5], 100)
        self.assertEqual(row[6], 20)
        self.assertEqual(row[7], "abc123")

    def test_log_http_error(self):
        from movietrace.logging.api_usage import log_api_call

        log_api_call(
            db_path=self.db_path,
            service="omdb",
            endpoint="/?i",
            operation="omdb_detail.get_by_imdb_id",
            request_date="2026-05-14",
            status="http_error",
            http_status=401,
            quota_error=True,
            error_message="Request limit reached!",
            key_fingerprint="def456",
        )

        row = self.conn.execute(
            "select service, status, http_status, quota_error, error_message, key_fingerprint from api_usage_log"
        ).fetchone()
        self.assertEqual(row[0], "omdb")
        self.assertEqual(row[1], "http_error")
        self.assertEqual(row[2], 401)
        self.assertEqual(row[3], 1)
        self.assertIn("limit reached", row[4])
        self.assertEqual(row[5], "def456")

    def test_log_rate_limited(self):
        from movietrace.logging.api_usage import log_api_call

        log_api_call(
            db_path=self.db_path,
            service="trakt",
            endpoint="/shows/trending",
            operation="trakt_trending.fetch_shows",
            request_date="2026-05-14",
            status="http_error",
            http_status=429,
            rate_limited=True,
            key_fingerprint="ghi789",
        )

        row = self.conn.execute(
            "select service, rate_limited, http_status from api_usage_log"
        ).fetchone()
        self.assertEqual(row[0], "trakt")
        self.assertEqual(row[1], 1)
        self.assertEqual(row[2], 429)

    def test_log_network_error(self):
        from movietrace.logging.api_usage import log_api_call

        log_api_call(
            db_path=self.db_path,
            service="flixpatrol",
            endpoint="/top10s",
            request_date="2026-05-14",
            status="network_error",
            error_message="Connection timed out",
            key_fingerprint="jkl012",
        )

        row = self.conn.execute(
            "select service, status, error_message from api_usage_log"
        ).fetchone()
        self.assertEqual(row[0], "flixpatrol")
        self.assertEqual(row[1], "network_error")
        self.assertEqual(row[2], "Connection timed out")

    def test_log_does_not_store_full_key(self):
        from movietrace.logging.api_usage import log_api_call

        secret = "actual-secret-api-key-value-12345"
        log_api_call(
            db_path=self.db_path,
            service="tmdb",
            endpoint="/test",
            request_date="2026-05-14",
            status="success",
            key_fingerprint="safe123abcde",
        )

        row = self.conn.execute(
            "select key_fingerprint, error_message, metadata_json from api_usage_log"
        ).fetchone()
        combined = f"{row[0]}|{row[1] or ''}|{row[2] or ''}"
        self.assertNotIn("actual-secret", combined)
        self.assertNotIn(secret, combined)

    def test_log_truncates_long_error(self):
        from movietrace.logging.api_usage import log_api_call

        long_msg = "x" * 1000
        log_api_call(
            db_path=self.db_path,
            service="tmdb",
            endpoint="/test",
            request_date="2026-05-14",
            status="http_error",
            error_message=long_msg,
            key_fingerprint="fp",
        )

        row = self.conn.execute(
            "select error_message from api_usage_log"
        ).fetchone()
        self.assertLessEqual(len(row[0]), 500)

    def test_log_never_raises(self):
        from movietrace.logging.api_usage import log_api_call

        # Invalid db_path should not raise
        log_api_call(
            db_path="/nonexistent/path/db.sqlite",
            service="tmdb",
            endpoint="/test",
            request_date="2026-05-14",
            status="success",
            key_fingerprint="fp",
        )
        # Should not have raised

    def test_metadata_sanitized(self):
        from movietrace.logging.api_usage import log_api_call

        log_api_call(
            db_path=self.db_path,
            service="tmdb",
            endpoint="/test",
            request_date="2026-05-14",
            status="success",
            key_fingerprint="fp",
            metadata={"url": "https://example.com", "apikey": "secret123", "page": 1},
        )

        row = self.conn.execute("select metadata_json from api_usage_log").fetchone()
        meta = row[0]
        self.assertIn("url", meta)
        self.assertIn("page", meta)
        self.assertNotIn("apikey", meta)
        self.assertNotIn("secret123", meta)

    def test_quota_error_and_rate_limited_are_exclusive_flags(self):
        from movietrace.logging.api_usage import log_api_call

        # OMDb quota error: quota_error=1, rate_limited=0
        log_api_call(
            db_path=self.db_path,
            service="omdb",
            endpoint="/?i",
            request_date="2026-05-14",
            status="http_error",
            http_status=401,
            quota_error=True,
            rate_limited=False,
            key_fingerprint="fp",
        )

        row = self.conn.execute(
            "select quota_error, rate_limited from api_usage_log"
        ).fetchone()
        self.assertEqual(row[0], 1)
        self.assertEqual(row[1], 0)


class ApiCallTrackerTest(unittest.TestCase):
    def test_tracker_elapsed_ms(self):
        import time
        from movietrace.logging.api_usage import ApiCallTracker

        tracker = ApiCallTracker(
            db_path="/tmp/test.db",
            service="tmdb",
            endpoint="/test",
            request_date="2026-05-14",
        )
        tracker.start()
        time.sleep(0.01)
        ms = tracker.elapsed_ms
        self.assertIsInstance(ms, int)
        self.assertGreater(ms, 0)


if __name__ == "__main__":
    unittest.main()
