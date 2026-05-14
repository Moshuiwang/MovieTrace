import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))


class SchemaMigration012Test(unittest.TestCase):
    def setUp(self):
        import sqlite3
        from movietrace.db.schema import initialize_database, connect_database

        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / "test_012.db"
        initialize_database(self.db_path)
        self.conn = connect_database(self.db_path)
        self.conn.row_factory = sqlite3.Row

    def tearDown(self):
        self.conn.close()
        self.tmpdir.cleanup()

    def test_schema_version_is_at_least_12(self):
        row = self.conn.execute(
            "select version from schema_migrations order by version desc limit 1"
        ).fetchone()
        self.assertGreaterEqual(row[0], 12)

    def test_source_fetch_runs_table_exists(self):
        rows = self.conn.execute("pragma table_info(source_fetch_runs)").fetchall()
        col_names = [r[1] for r in rows]
        for col in ("target_date", "source", "status", "source_snapshot_date",
                    "rows_fetched", "rows_inserted", "rows_used",
                    "error_message", "config_json", "started_at", "finished_at"):
            self.assertIn(col, col_names, f"Missing column: {col}")

    def test_unique_constraint_enforced(self):
        from movietrace.pipeline.source_fetch_status import record_source_fetch_run
        record_source_fetch_run(self.conn, "2026-05-14", "tmdb", "fresh",
                                rows_fetched=50, rows_inserted=45)
        self.conn.commit()
        # Should not raise — upserts instead
        record_source_fetch_run(self.conn, "2026-05-14", "tmdb", "fallback",
                                rows_fetched=30, rows_inserted=25)
        self.conn.commit()
        row = self.conn.execute(
            "select status, rows_fetched from source_fetch_runs where target_date=? and source=?",
            ("2026-05-14", "tmdb"),
        ).fetchone()
        self.assertEqual(row[0], "fallback")
        self.assertEqual(row[1], 30)

    def test_migration_012_idempotent(self):
        from movietrace.db.schema import initialize_database

        initialize_database(self.db_path)
        version = self.conn.execute(
            "select version from schema_migrations where version=12"
        ).fetchone()
        self.assertIsNotNone(version)


if __name__ == "__main__":
    unittest.main()
