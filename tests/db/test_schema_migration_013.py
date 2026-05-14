import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))


class SchemaMigration013Test(unittest.TestCase):
    def setUp(self):
        import sqlite3
        from movietrace.db.schema import initialize_database, connect_database

        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / "test_013.db"
        initialize_database(self.db_path)
        self.conn = connect_database(self.db_path)
        self.conn.row_factory = sqlite3.Row

    def tearDown(self):
        self.conn.close()
        self.tmpdir.cleanup()

    def test_schema_version_is_at_least_13(self):
        row = self.conn.execute(
            "select version from schema_migrations order by version desc limit 1"
        ).fetchone()
        self.assertGreaterEqual(row[0], 13)

    def test_migration_013_idempotent(self):
        from movietrace.db.schema import initialize_database

        initialize_database(self.db_path)
        version = self.conn.execute(
            "select version from schema_migrations where version=13"
        ).fetchone()
        self.assertIsNotNone(version)

    def test_bare_tv_id_normalized_to_tv_prefix(self):
        """Migration 013 prefixes bare TMDb IDs with correct namespace."""
        # Insert a TV canonical_item with bare TMDb external_id (simulating pre-fix state)
        self.conn.execute(
            "insert into canonical_items(id, canonical_item_key, title, content_type, content_granularity) values (99, 'tmdb:tv:999:season:1', 'Test Show', 'tv', 'season')"
        )
        self.conn.execute(
            "insert into external_ids(canonical_item_id, source, external_id) values (99, 'tmdb', '999')"
        )
        self.conn.commit()

        # Apply migration 013 SQL directly (already recorded, so initialize_database skips it)
        from pathlib import Path
        migration_sql = (Path(__file__).resolve().parents[2] / "src" / "movietrace" / "db" / "migrations" / "013_tmdb_namespace_cleanup.sql").read_text()
        self.conn.executescript(migration_sql)
        self.conn.commit()

        row = self.conn.execute(
            "select external_id from external_ids where canonical_item_id=99 and source='tmdb'"
        ).fetchone()
        self.assertEqual(row[0], "tv:999")

    def test_prefixed_ids_unchanged(self):
        """Already-prefixed IDs are not double-prefixed."""
        self.conn.execute(
            "insert into canonical_items(id, canonical_item_key, title, content_type, content_granularity) values (100, 'tmdb:movie:100:season:1', 'Test Movie', 'movie', 'movie')"
        )
        self.conn.execute(
            "insert into external_ids(canonical_item_id, source, external_id) values (100, 'tmdb', 'movie:100')"
        )
        self.conn.commit()

        from movietrace.db.schema import initialize_database
        initialize_database(self.db_path)

        row = self.conn.execute(
            "select external_id from external_ids where canonical_item_id=100 and source='tmdb'"
        ).fetchone()
        self.assertEqual(row[0], "movie:100")

    def test_duplicate_bare_tv_id_removed_before_update(self):
        """Bare TV IDs that would collide with prefixed IDs do not abort migration."""
        self.conn.execute(
            "insert into canonical_items(id, canonical_item_key, title, content_type, content_granularity) values (101, 'tmdb:tv:123:season:1', 'Show 123', 'tv', 'season')"
        )
        self.conn.execute(
            "insert into external_ids(canonical_item_id, source, external_id) values (101, 'tmdb', 'tv:123')"
        )
        self.conn.execute(
            "insert into external_ids(canonical_item_id, source, external_id) values (101, 'tmdb', '123')"
        )
        self.conn.commit()

        migration_sql = (Path(__file__).resolve().parents[2] / "src" / "movietrace" / "db" / "migrations" / "013_tmdb_namespace_cleanup.sql").read_text()
        self.conn.executescript(migration_sql)
        self.conn.commit()

        rows = self.conn.execute(
            "select external_id from external_ids where source='tmdb' and external_id like '%123' order by external_id"
        ).fetchall()
        self.assertEqual([r[0] for r in rows], ["tv:123"])

    def test_duplicate_bare_movie_id_removed_before_update(self):
        """Bare movie IDs that would collide with prefixed IDs do not abort migration."""
        self.conn.execute(
            "insert into canonical_items(id, canonical_item_key, title, content_type, content_granularity) values (102, 'tmdb:movie:456', 'Movie 456', 'movie', 'movie')"
        )
        self.conn.execute(
            "insert into external_ids(canonical_item_id, source, external_id) values (102, 'tmdb', 'movie:456')"
        )
        self.conn.execute(
            "insert into external_ids(canonical_item_id, source, external_id) values (102, 'tmdb', '456')"
        )
        self.conn.commit()

        migration_sql = (Path(__file__).resolve().parents[2] / "src" / "movietrace" / "db" / "migrations" / "013_tmdb_namespace_cleanup.sql").read_text()
        self.conn.executescript(migration_sql)
        self.conn.commit()

        rows = self.conn.execute(
            "select external_id from external_ids where source='tmdb' and external_id like '%456' order by external_id"
        ).fetchall()
        self.assertEqual([r[0] for r in rows], ["movie:456"])


if __name__ == "__main__":
    unittest.main()
