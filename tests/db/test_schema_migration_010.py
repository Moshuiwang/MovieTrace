import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))


class SchemaMigration010Test(unittest.TestCase):
    def setUp(self):
        from movietrace.db.schema import initialize_database, connect_database

        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / "test_010.db"
        initialize_database(self.db_path)
        self.conn = connect_database(self.db_path)

    def tearDown(self):
        self.conn.close()
        self.tmpdir.cleanup()

    def test_schema_version_is_at_least_10(self):
        row = self.conn.execute(
            "select version from schema_migrations order by version desc limit 1"
        ).fetchone()
        self.assertGreaterEqual(row[0], 10)

    def test_fp_new_columns_exist(self):
        rows = self.conn.execute("pragma table_info(flixpatrol_top10)").fetchall()
        col_names = [r[1] for r in rows]
        for col in ("updated_at", "country_id", "company_id"):
            self.assertIn(col, col_names, f"Missing FP column: {col}")

    def test_trakt_new_columns_exist(self):
        rows = self.conn.execute("pragma table_info(trakt_trending)").fetchall()
        col_names = [r[1] for r in rows]
        for col in ("genres_json", "trakt_status", "country", "network",
                    "runtime", "overview", "first_aired", "aired_episodes",
                    "certification", "updated_at"):
            self.assertIn(col, col_names, f"Missing Trakt column: {col}")

    def test_migration_010_idempotent(self):
        from movietrace.db.schema import initialize_database

        initialize_database(self.db_path)
        version = self.conn.execute(
            "select version from schema_migrations where version=10"
        ).fetchone()
        self.assertIsNotNone(version)


if __name__ == "__main__":
    unittest.main()
