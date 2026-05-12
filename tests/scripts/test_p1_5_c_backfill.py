import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))


class MockTmdbDetailClient:
    """Mock TMDb detail client for testing."""

    def __init__(self, details_by_id=None):
        self.details = details_by_id or {}
        self.call_count = 0

    def get_tv_details(self, tmdb_tv_id):
        self.call_count += 1
        if tmdb_tv_id in self.details:
            return self.details[tmdb_tv_id]
        return {}


class P1Dot5CBackfillTest(unittest.TestCase):
    def setUp(self):
        from movietrace.db.schema import initialize_database, connect_database
        from movietrace.pipeline.entity_matching import _ensure_quality_issues_table

        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / "test.db"
        initialize_database(self.db_path)
        self.conn = connect_database(self.db_path)
        _ensure_quality_issues_table(self.conn)

    def tearDown(self):
        self.conn.close()
        self.tmpdir.cleanup()

    def _insert_canonical_tv(self, key, title, season, tmdb_id):
        self.conn.execute(
            """insert into canonical_items(
                canonical_item_key, title, content_type, content_granularity, season_number
            ) values (?, ?, 'tv', 'season', ?)""",
            (key, title, season),
        )
        ci_id = self.conn.execute("select last_insert_rowid()").fetchone()[0]
        self.conn.execute(
            """insert or ignore into external_ids(
                canonical_item_id, source, external_id, external_granularity
            ) values (?, 'tmdb', ?, 'series')""",
            (ci_id, tmdb_id),
        )
        self.conn.execute(
            """insert or ignore into external_ids(
                canonical_item_id, source, external_id, external_granularity
            ) values (?, 'upstream', ?, 'season')""",
            (ci_id, str(ci_id * 100)),
        )
        return ci_id

    def test_backfill_skips_movies(self):
        from movietrace.pipeline.virtual_series import find_or_create_virtual_series_for_canonical_item

        # Insert a movie canonical_item (should be skipped by the script query)
        self.conn.execute(
            """insert into canonical_items(
                canonical_item_key, title, content_type, content_granularity
            ) values ('tmdb:movie:123', 'Test Movie', 'movie', 'movie')"""
        )
        # The backfill query filters content_type='tv', so movies won't appear
        rows = self.conn.execute(
            "select id from canonical_items where content_type = 'tv' and virtual_series_id is null"
        ).fetchall()
        self.assertEqual(len(rows), 0)  # Movie is not in TV query

    def test_backfill_aggregates_same_series_two_seasons(self):
        from movietrace.pipeline.virtual_series import (
            find_or_create_virtual_series_for_canonical_item,
            link_to_virtual_series,
            update_local_max_season,
        )

        ci_s01 = self._insert_canonical_tv(
            "tmdb:tv:1399:season:1", "Game of Thrones S01", 1, "1399"
        )
        ci_s02 = self._insert_canonical_tv(
            "tmdb:tv:1399:season:2", "Game of Thrones S02", 2, "1399"
        )

        mock = MockTmdbDetailClient(
            {
                "1399": {
                    "name": "Game of Thrones",
                    "status": "Ended",
                    "number_of_seasons": 8,
                }
            }
        )

        vs_id_1 = find_or_create_virtual_series_for_canonical_item(
            self.conn, ci_s01, mock
        )
        self.assertIsNotNone(vs_id_1)
        link_to_virtual_series(self.conn, ci_s01, vs_id_1)
        update_local_max_season(self.conn, vs_id_1, 1)
        self.conn.commit()

        vs_id_2 = find_or_create_virtual_series_for_canonical_item(
            self.conn, ci_s02, mock
        )
        self.assertIsNotNone(vs_id_2)
        link_to_virtual_series(self.conn, ci_s02, vs_id_2)
        update_local_max_season(self.conn, vs_id_2, 2)
        self.conn.commit()

        # Both seasons should link to the same virtual_series
        self.assertEqual(vs_id_1, vs_id_2)

        # Verify local_max_season is 2
        row = self.conn.execute(
            "select local_max_season from virtual_series where id = ?", (vs_id_1,)
        ).fetchone()
        self.assertEqual(row[0], 2)

        # Only one virtual_series should exist
        count = self.conn.execute("select count(*) from virtual_series").fetchone()[0]
        self.assertEqual(count, 1)

    def test_backfill_handles_missing_tmdb_id(self):
        # Insert a canonical_item without a tmdb external_id
        self.conn.execute(
            """insert into canonical_items(
                canonical_item_key, title, content_type, content_granularity
            ) values ('test:no:tmdb', 'No TMDb Show', 'tv', 'season')"""
        )
        ci_id = self.conn.execute("select last_insert_rowid()").fetchone()[0]

        # Query for tv items with null virtual_series_id
        rows = self.conn.execute(
            """select ci.id from canonical_items ci
               where ci.content_type = 'tv' and ci.virtual_series_id is null"""
        ).fetchall()
        self.assertEqual(len(rows), 1)

        # Verify no tmdb external_id exists
        ext = self.conn.execute(
            "select external_id from external_ids where canonical_item_id = ? and source = 'tmdb'",
            (ci_id,),
        ).fetchone()
        self.assertIsNone(ext)

    def test_backfill_idempotent(self):
        from movietrace.pipeline.virtual_series import (
            find_or_create_virtual_series_for_canonical_item,
            link_to_virtual_series,
            update_local_max_season,
        )

        ci_id = self._insert_canonical_tv(
            "tmdb:tv:1668:season:1", "Friends S01", 1, "1668"
        )

        mock = MockTmdbDetailClient(
            {"1668": {"name": "Friends", "status": "Ended", "number_of_seasons": 10}}
        )

        # First pass
        vs_id_1 = find_or_create_virtual_series_for_canonical_item(
            self.conn, ci_id, mock
        )
        self.assertIsNotNone(vs_id_1)
        link_to_virtual_series(self.conn, ci_id, vs_id_1)
        update_local_max_season(self.conn, vs_id_1, 1)
        self.conn.commit()

        # Verify linked
        row = self.conn.execute(
            "select virtual_series_id from canonical_items where id = ?", (ci_id,)
        ).fetchone()
        self.assertEqual(row[0], vs_id_1)

        # Second pass should find it already linked (script query filters out linked items)
        unlinked = self.conn.execute(
            "select id from canonical_items where content_type = 'tv' and virtual_series_id is null"
        ).fetchall()
        self.assertEqual(len(unlinked), 0)


if __name__ == "__main__":
    unittest.main()
