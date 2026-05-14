import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))


class SchemaMigration014Test(unittest.TestCase):
    def setUp(self):
        import sqlite3
        from movietrace.db.schema import initialize_database, connect_database

        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / "test_014.db"
        initialize_database(self.db_path)
        self.conn = connect_database(self.db_path)
        self.conn.row_factory = sqlite3.Row

    def tearDown(self):
        self.conn.close()
        self.tmpdir.cleanup()

    def test_schema_version_at_least_14(self):
        row = self.conn.execute(
            "select version from schema_migrations order by version desc limit 1"
        ).fetchone()
        self.assertGreaterEqual(row[0], 14)

    def test_old_index_gone(self):
        """ux_content_updates_item_type must not exist after migration 014."""
        indexes = {
            r[1]
            for r in self.conn.execute("pragma index_list(content_updates)").fetchall()
        }
        self.assertNotIn("ux_content_updates_item_type", indexes)

    def test_new_index_exists(self):
        """ux_content_updates_update_id must exist after migration 014."""
        indexes = {
            r[1]
            for r in self.conn.execute("pragma index_list(content_updates)").fetchall()
        }
        self.assertIn("ux_content_updates_update_id", indexes)

    def test_content_update_id_unique_enforced(self):
        """Duplicate content_update_id triggers constraint violation."""
        self.conn.execute(
            """insert into canonical_items(id, canonical_item_key, title, content_type, content_granularity)
               values (1, 'k1', 'Test', 'movie', 'movie')"""
        )
        self.conn.execute(
            """insert or ignore into content_updates(content_update_id, canonical_item_id, update_type)
               values ('discovery:100:2026-05-14', 1, 'new_discovery')"""
        )
        self.conn.commit()

        with self.assertRaises(Exception):
            self.conn.execute(
                """insert into content_updates(content_update_id, canonical_item_id, update_type)
                   values ('discovery:100:2026-05-14', 1, 'new_discovery')"""
            )

    def test_same_content_different_days_allowed(self):
        """Same (canonical_item_id, update_type) but different content_update_id → both written."""
        self.conn.execute(
            """insert into canonical_items(id, canonical_item_key, title, content_type, content_granularity)
               values (1, 'k1', 'Test', 'movie', 'movie')"""
        )
        # Day 1
        self.conn.execute(
            """insert into content_updates(content_update_id, canonical_item_id, update_type)
               values ('discovery:100:2026-05-13', 1, 'new_discovery')"""
        )
        # Day 2 — same canonical, same type, different date → OK (event history model)
        self.conn.execute(
            """insert into content_updates(content_update_id, canonical_item_id, update_type)
               values ('discovery:100:2026-05-14', 1, 'new_discovery')"""
        )
        self.conn.commit()
        count = self.conn.execute(
            "select count(*) from content_updates where canonical_item_id=1 and update_type='new_discovery'"
        ).fetchone()[0]
        self.assertEqual(count, 2)

    def test_migration_014_idempotent(self):
        from movietrace.db.schema import initialize_database
        initialize_database(self.db_path)
        version = self.conn.execute(
            "select version from schema_migrations where version=14"
        ).fetchone()
        self.assertIsNotNone(version)


if __name__ == "__main__":
    unittest.main()
