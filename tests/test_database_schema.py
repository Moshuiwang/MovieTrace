import sqlite3
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
                versions = [
                    row[0]
                    for row in conn.execute(
                        "select version from schema_migrations"
                    )
                ]

        self.assertEqual(foreign_keys, 1)
        self.assertEqual(max(versions), 19)
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
                "feishu_sync_failures",
                "current_discovery_items",
                "discovery_observations",
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
        self.assertIn("ux_current_discovery_items_key", indexes)
        self.assertIn("ux_current_discovery_items_type_tmdb", indexes)
        self.assertIn("ix_current_discovery_items_last_discovered_date", indexes)
        self.assertIn("ux_discovery_observations_key_date", indexes)
        self.assertIn("ix_discovery_observations_observed_date", indexes)

    def test_discovery_observations_are_unique_per_key_and_date(self):
        from movietrace.db.schema import connect_database, initialize_database

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "movietrace.db"
            initialize_database(db_path)

            with connect_database(db_path) as conn:
                conn.execute(
                    """
                    insert into current_discovery_items
                        (discovery_key, content_type, tmdb_id, title,
                         first_discovered_date, last_discovered_date)
                    values (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "discovery:tv:123",
                        "tv",
                        123,
                        "Example",
                        "2026-05-24",
                        "2026-05-24",
                    ),
                )
                conn.execute(
                    """
                    insert into discovery_observations
                        (discovery_key, observed_date, hot_score, priority)
                    values (?, ?, ?, ?)
                    """,
                    ("discovery:tv:123", "2026-05-24", 88.5, "P1"),
                )

                with self.assertRaises(sqlite3.IntegrityError):
                    conn.execute(
                        """
                        insert into discovery_observations
                            (discovery_key, observed_date, hot_score, priority)
                        values (?, ?, ?, ?)
                        """,
                        ("discovery:tv:123", "2026-05-24", 90.0, "P0"),
                    )

    def test_current_discovery_key_must_match_type_and_tmdb_id(self):
        from movietrace.db.schema import connect_database, initialize_database

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "movietrace.db"
            initialize_database(db_path)

            with connect_database(db_path) as conn:
                valid_insert = """
                    insert into current_discovery_items
                        (discovery_key, content_type, tmdb_id,
                         first_discovered_date, last_discovered_date)
                    values (?, ?, ?, ?, ?)
                    """
                conn.execute(
                    valid_insert,
                    (
                        "discovery:tv:123",
                        "tv",
                        123,
                        "2026-05-24",
                        "2026-05-24",
                    ),
                )

                invalid_rows = [
                    ("discovery:tv:123:2026-05-24", "tv", 123),
                    ("discovery:movie:123", "tv", 123),
                    ("discovery:tv:456", "tv", 123),
                ]
                for discovery_key, content_type, tmdb_id in invalid_rows:
                    with self.assertRaises(sqlite3.IntegrityError):
                        conn.execute(
                            valid_insert,
                            (
                                discovery_key,
                                content_type,
                                tmdb_id,
                                "2026-05-24",
                                "2026-05-24",
                            ),
                        )


if __name__ == "__main__":
    unittest.main()
