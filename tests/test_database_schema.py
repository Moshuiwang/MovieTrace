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
        # Active tables (migration 016 drops legacy pre-flip tables)
        # baseline_quality_issues is created by entity_matching.py at runtime, not by initialize_database
        self.assertTrue(
            {
                "schema_migrations",
                "canonical_items",
                "external_ids",
                "content_updates",
                "api_cache",
                "upstream_programs",
                "upstream_episodes",
                "virtual_series",
            }.issubset(tables)
        )
        # Legacy tables must NOT exist after migration 016
        for dropped in ("feishu_import_runs", "source_records", "baseline_items",
                        "candidates", "candidate_matches", "match_candidates"):
            self.assertNotIn(dropped, tables, f"{dropped} should be dropped by migration 016")
        self.assertIn("ux_canonical_items_key", indexes)
        self.assertIn("ux_external_ids_source_id", indexes)
        self.assertIn("ux_content_updates_update_id", indexes)
        self.assertIn("ux_virtual_series_tmdb_tv_id", indexes)
        self.assertIn("idx_canonical_items_virtual_series", indexes)


if __name__ == "__main__":
    unittest.main()
