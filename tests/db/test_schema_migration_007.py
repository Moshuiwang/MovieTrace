import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))


class SchemaMigration007Test(unittest.TestCase):
    def setUp(self):
        from movietrace.db.schema import initialize_database, connect_database

        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / "test_007.db"
        initialize_database(self.db_path)
        self.conn = connect_database(self.db_path)

    def tearDown(self):
        self.conn.close()
        self.tmpdir.cleanup()

    # --- tmdb_trending ---

    def test_tmdb_trending_table_exists(self):
        row = self.conn.execute(
            "select name from sqlite_master where type='table' and name='tmdb_trending'"
        ).fetchone()
        self.assertIsNotNone(row)

    def test_tmdb_trending_all_columns(self):
        rows = self.conn.execute("pragma table_info(tmdb_trending)").fetchall()
        col_names = [r[1] for r in rows]
        expected = [
            "id", "tmdb_id", "media_type", "title", "original_title",
            "release_date", "original_language", "popularity", "vote_average",
            "vote_count", "source_endpoint", "source_page", "snapshot_date",
            "raw_payload_json", "collected_at",
        ]
        for col in expected:
            self.assertIn(col, col_names)

    def test_tmdb_trending_unique_constraint(self):
        self.conn.execute(
            "insert into tmdb_trending(tmdb_id,media_type,title,popularity,source_endpoint,source_page,snapshot_date,raw_payload_json)"
            " values (123,'movie','Test',10.0,'trending/day',1,'2026-05-13','{}')"
        )
        self.conn.commit()
        with self.assertRaises(Exception):
            self.conn.execute(
                "insert into tmdb_trending(tmdb_id,media_type,title,popularity,source_endpoint,source_page,snapshot_date,raw_payload_json)"
                " values (123,'movie','Test',10.0,'trending/day',1,'2026-05-13','{}')"
            )

    def test_tmdb_trending_indexes_exist(self):
        rows = self.conn.execute(
            "select name from sqlite_master where type='index' and tbl_name='tmdb_trending'"
        ).fetchall()
        names = [r[0] for r in rows]
        self.assertIn("ux_tmdb_trending_dedup", names)
        self.assertIn("idx_tmdb_trending_snapshot_date", names)
        self.assertIn("idx_tmdb_trending_tmdb_id", names)

    # --- trakt_trending ---

    def test_trakt_trending_table_exists(self):
        row = self.conn.execute(
            "select name from sqlite_master where type='table' and name='trakt_trending'"
        ).fetchone()
        self.assertIsNotNone(row)

    def test_trakt_trending_all_columns(self):
        rows = self.conn.execute("pragma table_info(trakt_trending)").fetchall()
        col_names = [r[1] for r in rows]
        expected = [
            "id", "trakt_id", "tmdb_id", "imdb_id", "media_type",
            "title", "year", "watchers", "rating", "votes",
            "source_endpoint", "snapshot_date", "raw_payload_json", "collected_at",
        ]
        for col in expected:
            self.assertIn(col, col_names)

    def test_trakt_trending_unique_constraint(self):
        self.conn.execute(
            "insert into trakt_trending(trakt_id,media_type,title,watchers,source_endpoint,snapshot_date,raw_payload_json)"
            " values (456,'movie','Test Movie',500,'movies/trending','2026-05-13','{}')"
        )
        self.conn.commit()
        with self.assertRaises(Exception):
            self.conn.execute(
                "insert into trakt_trending(trakt_id,media_type,title,watchers,source_endpoint,snapshot_date,raw_payload_json)"
                " values (456,'movie','Test Movie',500,'movies/trending','2026-05-13','{}')"
            )

    def test_trakt_trending_indexes_exist(self):
        rows = self.conn.execute(
            "select name from sqlite_master where type='index' and tbl_name='trakt_trending'"
        ).fetchall()
        names = [r[0] for r in rows]
        self.assertIn("ux_trakt_trending_dedup", names)
        self.assertIn("idx_trakt_trending_snapshot_date", names)
        self.assertIn("idx_trakt_trending_tmdb_id", names)

    # --- migration idempotency ---

    def test_migration_007_idempotent(self):
        from movietrace.db.schema import initialize_database

        initialize_database(self.db_path)
        version = self.conn.execute(
            "select version from schema_migrations where version=7"
        ).fetchone()
        self.assertIsNotNone(version)

    # --- existing tables untouched ---

    def test_flixpatrol_top10_still_exists(self):
        row = self.conn.execute(
            "select name from sqlite_master where type='table' and name='flixpatrol_top10'"
        ).fetchone()
        self.assertIsNotNone(row)

    def test_schema_migrations_has_version_7(self):
        row = self.conn.execute(
            "select version from schema_migrations order by version desc limit 1"
        ).fetchone()
        self.assertEqual(row[0], 7)


if __name__ == "__main__":
    unittest.main()
