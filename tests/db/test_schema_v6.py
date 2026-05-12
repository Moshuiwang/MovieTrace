import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))


class SchemaV6Test(unittest.TestCase):
    def setUp(self):
        from movietrace.db.schema import initialize_database, connect_database

        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / "test_v6.db"
        initialize_database(self.db_path)
        self.conn = connect_database(self.db_path)

    def tearDown(self):
        self.conn.close()
        self.tmpdir.cleanup()

    def test_virtual_series_table_exists(self):
        row = self.conn.execute(
            "select name from sqlite_master where type='table' and name='virtual_series'"
        ).fetchone()
        self.assertIsNotNone(row)

    def test_virtual_series_tmdb_tv_id_unique(self):
        rows = self.conn.execute(
            "select name from sqlite_master where type='index' and name='ux_virtual_series_tmdb_tv_id'"
        ).fetchall()
        self.assertEqual(len(rows), 1)

    def test_canonical_items_has_virtual_series_id_column(self):
        rows = self.conn.execute("pragma table_info(canonical_items)").fetchall()
        col_names = [r[1] for r in rows]
        self.assertIn("virtual_series_id", col_names)

    def test_content_updates_has_match_confidence_low_column(self):
        rows = self.conn.execute("pragma table_info(content_updates)").fetchall()
        col_names = [r[1] for r in rows]
        self.assertIn("match_confidence_low", col_names)

    def test_match_confidence_low_default_value(self):
        row = self.conn.execute(
            "pragma table_info(content_updates)"
        ).fetchall()
        for col in row:
            if col[1] == "match_confidence_low":
                self.assertEqual(col[4], "0")  # dflt_value
                break

    def test_migration_006_idempotent(self):
        from movietrace.db.schema import initialize_database

        # Running initialize_database again should not fail
        initialize_database(self.db_path)
        version = self.conn.execute(
            "select version from schema_migrations where version=6"
        ).fetchone()
        self.assertIsNotNone(version)


if __name__ == "__main__":
    unittest.main()
