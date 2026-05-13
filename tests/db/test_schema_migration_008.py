import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))


class SchemaMigration008Test(unittest.TestCase):
    def setUp(self):
        from movietrace.db.schema import initialize_database, connect_database

        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / "test_008.db"
        initialize_database(self.db_path)
        self.conn = connect_database(self.db_path)

    def tearDown(self):
        self.conn.close()
        self.tmpdir.cleanup()

    def test_api_usage_log_table_exists(self):
        row = self.conn.execute(
            "select name from sqlite_master where type='table' and name='api_usage_log'"
        ).fetchone()
        self.assertIsNotNone(row)

    def test_api_usage_log_all_columns(self):
        rows = self.conn.execute("pragma table_info(api_usage_log)").fetchall()
        col_names = [r[1] for r in rows]
        expected = [
            "id", "service", "endpoint", "operation", "request_date",
            "started_at", "finished_at", "status", "http_status",
            "cache_status", "quota_error", "rate_limited", "duration_ms",
            "item_count", "error_code", "error_message",
            "key_fingerprint", "metadata_json",
        ]
        for col in expected:
            self.assertIn(col, col_names)

    def test_api_usage_log_indexes_exist(self):
        rows = self.conn.execute(
            "select name from sqlite_master where type='index' and tbl_name='api_usage_log'"
        ).fetchall()
        names = [r[0] for r in rows]
        self.assertIn("idx_api_usage_log_service", names)
        self.assertIn("idx_api_usage_log_status", names)
        self.assertIn("idx_api_usage_log_endpoint", names)
        self.assertIn("idx_api_usage_log_quota", names)

    def test_can_insert_usage_log(self):
        self.conn.execute(
            """insert into api_usage_log(
                service, endpoint, operation, request_date, status,
                http_status, quota_error, rate_limited, duration_ms, key_fingerprint
            ) values ('tmdb','/test','op.test','2026-05-14','success',200,0,0,150,'abc123')"""
        )
        self.conn.commit()
        row = self.conn.execute(
            "select service, status, key_fingerprint from api_usage_log where service='tmdb'"
        ).fetchone()
        self.assertEqual(row[0], "tmdb")
        self.assertEqual(row[1], "success")
        self.assertEqual(row[2], "abc123")

    def test_migration_008_idempotent(self):
        from movietrace.db.schema import initialize_database

        initialize_database(self.db_path)
        version = self.conn.execute(
            "select version from schema_migrations where version=8"
        ).fetchone()
        self.assertIsNotNone(version)

    def test_schema_version_is_8(self):
        row = self.conn.execute(
            "select version from schema_migrations order by version desc limit 1"
        ).fetchone()
        self.assertGreaterEqual(row[0], 8)

    def test_existing_tables_still_exist(self):
        for tbl in ("canonical_items", "flixpatrol_top10", "tmdb_trending", "trakt_trending"):
            row = self.conn.execute(
                f"select name from sqlite_master where type='table' and name='{tbl}'"
            ).fetchone()
            self.assertIsNotNone(row, f"Table {tbl} should exist")


if __name__ == "__main__":
    unittest.main()
