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

    def test_migration_namespaces_legacy_discovery_ids_before_unique_index(self):
        import sqlite3

        conn = sqlite3.connect(":memory:")
        conn.executescript(
            """
            create table schema_migrations (
                version integer primary key,
                applied_at text not null default current_timestamp
            );
            create table canonical_items (
                id integer primary key autoincrement,
                canonical_item_key text not null,
                title text not null,
                content_type text,
                content_granularity text not null
            );
            create table content_updates (
                id integer primary key autoincrement,
                content_update_id text not null,
                canonical_item_id integer not null references canonical_items(id),
                update_type text not null
            );
            create unique index ux_content_updates_item_type
            on content_updates(canonical_item_id, update_type);
            insert into canonical_items
                (id, canonical_item_key, title, content_type, content_granularity)
            values
                (1, 'tmdb:movie:100', 'Movie 100', 'movie', 'movie'),
                (2, 'tmdb:tv:100:season:1', 'Show 100', 'tv', 'season');
            insert into content_updates
                (content_update_id, canonical_item_id, update_type)
            values
                ('discovery:100:2026-05-14', 1, 'new_discovery'),
                ('discovery:100:2026-05-14', 2, 'new_discovery');
            """
        )

        migration_sql = (
            Path(__file__).resolve().parents[2]
            / "src"
            / "movietrace"
            / "db"
            / "migrations"
            / "014_content_updates_event_history.sql"
        ).read_text()
        conn.executescript(migration_sql)

        rows = conn.execute(
            "select content_update_id from content_updates order by canonical_item_id"
        ).fetchall()
        self.assertEqual(
            rows,
            [
                ("discovery:movie:100:2026-05-14",),
                ("discovery:tv:100:2026-05-14",),
            ],
        )
        indexes = {r[1] for r in conn.execute("pragma index_list(content_updates)")}
        self.assertIn("ux_content_updates_update_id", indexes)
        conn.close()

    def test_migration_014_idempotent(self):
        from movietrace.db.schema import initialize_database
        initialize_database(self.db_path)
        version = self.conn.execute(
            "select version from schema_migrations where version=14"
        ).fetchone()
        self.assertIsNotNone(version)

    def test_schema_12_database_upgrades_to_14_with_realistic_legacy_data(self):
        import sqlite3
        from movietrace.db.schema import initialize_database

        legacy_path = Path(self.tmpdir.name) / "legacy_v12.db"
        conn = sqlite3.connect(legacy_path)
        conn.executescript(
            """
            create table schema_migrations (
                version integer primary key,
                applied_at text not null default current_timestamp
            );
            insert into schema_migrations(version) values
                (1),(2),(3),(4),(5),(6),(7),(8),(9),(10),(11),(12);

            create table canonical_items (
                id integer primary key autoincrement,
                canonical_item_key text not null,
                title text not null,
                content_type text,
                content_granularity text not null,
                parent_canonical_item_id integer,
                season_number integer,
                episode_number integer,
                virtual_series_id integer
            );
            create unique index ux_canonical_items_key
            on canonical_items(canonical_item_key);

            create table external_ids (
                id integer primary key autoincrement,
                canonical_item_id integer not null references canonical_items(id) on delete cascade,
                source text not null,
                external_id text not null,
                external_granularity text,
                created_at text not null default current_timestamp
            );
            create unique index ux_external_ids_source_id
            on external_ids(source, external_id);

            create table content_updates (
                id integer primary key autoincrement,
                content_update_id text not null,
                canonical_item_id integer not null references canonical_items(id),
                update_type text not null,
                priority text,
                hot_score integer,
                baseline_match_status text,
                review_status text not null default 'pending',
                source_summary_json text,
                created_at text not null default current_timestamp,
                updated_at text not null default current_timestamp,
                match_confidence_low integer not null default 0
            );
            create unique index ux_content_updates_item_type
            on content_updates(canonical_item_id, update_type);

            insert into canonical_items
                (id, canonical_item_key, title, content_type, content_granularity)
            values
                (1, 'tmdb:tv:124364', 'FROM', 'tv', 'series'),
                (2, 'tmdb:movie:100', 'Movie 100', 'movie', 'movie'),
                (3, 'tmdb:tv:100:season:1', 'Show 100', 'tv', 'season');

            insert into external_ids(canonical_item_id, source, external_id)
            values
                (1, 'tmdb', 'tv:124364'),
                (1, 'tmdb', '124364'),
                (2, 'tmdb', 'movie:100'),
                (3, 'tmdb', 'tv:100');

            insert into content_updates(content_update_id, canonical_item_id, update_type)
            values
                ('discovery:124364:2026-05-13', 1, 'new_discovery'),
                ('discovery:100:2026-05-14', 2, 'new_discovery'),
                ('discovery:100:2026-05-14', 3, 'new_discovery');
            """
        )
        conn.commit()
        conn.close()

        initialize_database(legacy_path)

        conn = sqlite3.connect(legacy_path)
        version = conn.execute("select max(version) from schema_migrations").fetchone()[0]
        bare_tmdb_count = conn.execute(
            """select count(*) from external_ids
               where source='tmdb'
                 and external_id not like 'tv:%'
                 and external_id not like 'movie:%'
                 and external_id not like 'unknown:%'"""
        ).fetchone()[0]
        indexes = {r[1] for r in conn.execute("pragma index_list(content_updates)")}
        updates = [
            r[0]
            for r in conn.execute(
                "select content_update_id from content_updates order by canonical_item_id"
            ).fetchall()
        ]
        conn.close()

        self.assertGreaterEqual(version, 14)  # schema_version >= 14 (015+ may be applied)
        self.assertEqual(bare_tmdb_count, 0)
        self.assertNotIn("ux_content_updates_item_type", indexes)
        self.assertIn("ux_content_updates_update_id", indexes)
        self.assertEqual(
            updates,
            [
                "discovery:tv:124364:2026-05-13",
                "discovery:movie:100:2026-05-14",
                "discovery:tv:100:2026-05-14",
            ],
        )


if __name__ == "__main__":
    unittest.main()
