import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))


class VirtualSeriesTest(unittest.TestCase):
    def setUp(self):
        from movietrace.db.schema import initialize_database, connect_database

        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / "test.db"
        initialize_database(self.db_path)
        self.conn = connect_database(self.db_path)

    def tearDown(self):
        self.conn.close()
        self.tmpdir.cleanup()

    # --- derive_poll_priority ---

    def test_derive_poll_priority_returning(self):
        from movietrace.pipeline.virtual_series import derive_poll_priority

        self.assertEqual(derive_poll_priority("Returning Series"), "urgent")

    def test_derive_poll_priority_ended(self):
        from movietrace.pipeline.virtual_series import derive_poll_priority

        self.assertEqual(derive_poll_priority("Ended"), "low")

    def test_derive_poll_priority_canceled(self):
        from movietrace.pipeline.virtual_series import derive_poll_priority

        self.assertEqual(derive_poll_priority("Canceled"), "skip")

    def test_derive_poll_priority_unknown(self):
        from movietrace.pipeline.virtual_series import derive_poll_priority

        self.assertEqual(derive_poll_priority("Unknown Status"), "normal")

    # --- upsert_virtual_series ---

    def test_upsert_virtual_series_new(self):
        from movietrace.pipeline.virtual_series import upsert_virtual_series

        details = {"name": "Friends", "status": "Ended", "number_of_seasons": 10}
        vs_id = upsert_virtual_series(self.conn, "1668", details)

        self.assertIsInstance(vs_id, int)
        row = self.conn.execute(
            "select name, tmdb_status, tmdb_number_of_seasons, poll_priority "
            "from virtual_series where id = ?",
            (vs_id,),
        ).fetchone()
        self.assertEqual(row[0], "Friends")
        self.assertEqual(row[1], "Ended")
        self.assertEqual(row[2], 10)
        self.assertEqual(row[3], "low")

    def test_upsert_virtual_series_idempotent(self):
        from movietrace.pipeline.virtual_series import upsert_virtual_series

        details = {"name": "Friends", "status": "Ended", "number_of_seasons": 10}
        vs_id1 = upsert_virtual_series(self.conn, "1668", details)
        vs_id2 = upsert_virtual_series(self.conn, "1668", details)

        self.assertEqual(vs_id1, vs_id2)

    # --- extract_season_number ---

    def test_extract_season_number_from_name(self):
        from movietrace.pipeline.virtual_series import extract_season_number

        self.assertEqual(extract_season_number("Better Call Saul S01"), 1)
        self.assertEqual(extract_season_number("Friends S10"), 10)
        self.assertEqual(extract_season_number("The Simpsons S34"), 34)

    def test_extract_season_number_no_match_returns_none(self):
        from movietrace.pipeline.virtual_series import extract_season_number

        self.assertIsNone(extract_season_number("Avatar The Way of Water"))
        self.assertIsNone(extract_season_number("Inception"))

    # --- link_to_virtual_series ---

    def test_link_to_virtual_series(self):
        from movietrace.pipeline.virtual_series import (
            link_to_virtual_series,
            upsert_virtual_series,
        )

        # First create a canonical_item and virtual_series
        self.conn.execute(
            """insert into canonical_items(
                canonical_item_key, title, content_type, content_granularity, season_number
            ) values ('tmdb:tv:1668:season:1', 'Friends', 'tv', 'season', 1)"""
        )
        ci_id = self.conn.execute("select last_insert_rowid()").fetchone()[0]

        vs_id = upsert_virtual_series(
            self.conn, "1668", {"name": "Friends", "status": "Ended"}
        )

        link_to_virtual_series(self.conn, ci_id, vs_id)

        row = self.conn.execute(
            "select virtual_series_id from canonical_items where id = ?", (ci_id,)
        ).fetchone()
        self.assertEqual(row[0], vs_id)


if __name__ == "__main__":
    unittest.main()
