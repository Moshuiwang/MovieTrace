import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))


class SchemaMigration009Test(unittest.TestCase):
    def setUp(self):
        from movietrace.db.schema import initialize_database, connect_database

        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / "test_009.db"
        initialize_database(self.db_path)
        self.conn = connect_database(self.db_path)

    def tearDown(self):
        self.conn.close()
        self.tmpdir.cleanup()

    def test_schema_version_is_9(self):
        row = self.conn.execute(
            "select version from schema_migrations order by version desc limit 1"
        ).fetchone()
        self.assertGreaterEqual(row[0], 9)

    def test_new_tmdb_trending_columns_exist(self):
        rows = self.conn.execute("pragma table_info(tmdb_trending)").fetchall()
        col_names = [r[1] for r in rows]
        new_cols = [
            "adult", "softcore", "backdrop_path", "poster_path",
            "overview", "genre_ids_json", "origin_country_json",
            "first_air_date", "movie_release_date", "original_name",
            "last_air_date", "next_air_date", "last_episode_air_date",
            "last_episode_season_number", "last_episode_number",
            "number_of_seasons", "number_of_episodes", "tmdbtv_status",
            "in_production", "genres_json", "seasons_json",
            "last_episode_to_air_json", "next_episode_to_air_json",
            "networks_json", "production_companies_json",
            "spoken_languages_json", "created_by_json",
        ]
        for col in new_cols:
            self.assertIn(col, col_names, f"Missing column: {col}")

    def test_existing_columns_preserved(self):
        rows = self.conn.execute("pragma table_info(tmdb_trending)").fetchall()
        col_names = [r[1] for r in rows]
        old_cols = [
            "id", "tmdb_id", "media_type", "title", "original_title",
            "release_date", "original_language", "popularity",
            "vote_average", "vote_count", "source_endpoint", "source_page",
            "snapshot_date", "raw_payload_json", "collected_at",
        ]
        for col in old_cols:
            self.assertIn(col, col_names, f"Missing old column: {col}")

    def test_migration_009_idempotent(self):
        from movietrace.db.schema import initialize_database

        initialize_database(self.db_path)
        version = self.conn.execute(
            "select version from schema_migrations where version=9"
        ).fetchone()
        self.assertIsNotNone(version)

    def test_existing_tables_still_exist(self):
        for tbl in ("canonical_items", "flixpatrol_top10", "tmdb_trending", "api_usage_log"):
            row = self.conn.execute(
                f"select name from sqlite_master where type='table' and name='{tbl}'"
            ).fetchone()
            self.assertIsNotNone(row, f"Table {tbl} should exist")


if __name__ == "__main__":
    unittest.main()
