import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


class DatabaseSchemaTest(unittest.TestCase):
    def test_initialize_database_creates_core_tables_and_indexes(self):
        from movietrace.db.schema import initialize_database

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "movietrace.db"

            initialize_database(db_path)

            from movietrace.db.schema import connect_database

            with connect_database(db_path) as conn:
                tables = {
                    row[0]
                    for row in conn.execute(
                        "select name from sqlite_master where type = 'table'"
                    )
                }
                indexes = {
                    row[0]
                    for row in conn.execute(
                        "select name from sqlite_master where type = 'index'"
                    )
                }
                foreign_keys = conn.execute("pragma foreign_keys").fetchone()[0]

        self.assertEqual(foreign_keys, 1)
        self.assertTrue(
            {
                "schema_migrations",
                "feishu_import_runs",
                "source_records",
                "canonical_items",
                "external_ids",
                "baseline_items",
                "content_updates",
                "match_candidates",
                "api_cache",
            }.issubset(tables)
        )
        self.assertIn("ux_canonical_items_key", indexes)
        self.assertIn("ux_external_ids_source_id", indexes)
        self.assertIn("ux_content_updates_item_type", indexes)
        self.assertIn("idx_baseline_items_title", indexes)


if __name__ == "__main__":
    unittest.main()
