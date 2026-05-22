"""Migration 018 tests: feishu_sync_failures table creation."""

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))


class SchemaMigration018Test(unittest.TestCase):
    def setUp(self):
        import sqlite3
        from movietrace.db.schema import initialize_database, connect_database

        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / "test_018.db"
        initialize_database(self.db_path)
        self.conn = connect_database(self.db_path)
        self.conn.row_factory = sqlite3.Row

    def tearDown(self):
        self.conn.close()
        self.tmpdir.cleanup()

    def test_migration_018_creates_table_and_index(self):
        """feishu_sync_failures table and ix_feishu_sync_failures_unresolved index exist after migration."""
        # Table must exist
        row = self.conn.execute(
            "select name from sqlite_master where type='table' and name='feishu_sync_failures'"
        ).fetchone()
        self.assertIsNotNone(row, "feishu_sync_failures table should exist")

        # Index must exist
        idx = self.conn.execute(
            "select name from sqlite_master where type='index' and name='ix_feishu_sync_failures_unresolved'"
        ).fetchone()
        self.assertIsNotNone(idx, "ix_feishu_sync_failures_unresolved index should exist")

    def test_schema_version_is_18(self):
        """SCHEMA_VERSION constant should be 18."""
        from movietrace.db.schema import SCHEMA_VERSION
        self.assertEqual(SCHEMA_VERSION, 18)

    def test_migration_version_18_recorded(self):
        """schema_migrations should record version 18."""
        row = self.conn.execute(
            "select version from schema_migrations where version = 18"
        ).fetchone()
        self.assertIsNotNone(row)

    def test_table_columns(self):
        """feishu_sync_failures has the expected columns."""
        cols = {
            row[1]
            for row in self.conn.execute("pragma table_info(feishu_sync_failures)").fetchall()
        }
        expected = {
            "id", "synced_at", "table_id", "record_id", "operation",
            "payload_json", "error_code", "error_message", "retry_count", "resolved_at",
        }
        self.assertEqual(cols, expected)

    def test_can_insert_and_query_failure_record(self):
        """Insert a row into feishu_sync_failures and query it back."""
        self.conn.execute(
            """
            insert into feishu_sync_failures
                (table_id, operation, payload_json, error_message, retry_count)
            values ('tbl_abc', 'create', '{"title": "Test"}', 'timeout', 1)
            """
        )
        self.conn.commit()
        row = self.conn.execute(
            "select * from feishu_sync_failures where table_id='tbl_abc'"
        ).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["operation"], "create")
        self.assertIsNone(row["resolved_at"])

    def test_migration_018_idempotent(self):
        """Running initialize_database twice does not raise."""
        from movietrace.db.schema import initialize_database
        initialize_database(self.db_path)  # second run should be safe
        row = self.conn.execute(
            "select name from sqlite_master where type='table' and name='feishu_sync_failures'"
        ).fetchone()
        self.assertIsNotNone(row)


if __name__ == "__main__":
    unittest.main()
