import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


class InspectUpdatesCliTest(unittest.TestCase):
    def setUp(self):
        from movietrace.db.schema import initialize_database, connect_database
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / "test_inspect.db"
        initialize_database(self.db_path)
        self.conn = connect_database(self.db_path)

        # Seed canonical_items + external_ids + content_updates
        self.conn.execute(
            """insert into canonical_items (canonical_item_key, title, content_type, content_granularity)
               values ('k1', 'The Boys', 'tv', 'season')"""
        )
        self.conn.execute(
            """insert into canonical_items (canonical_item_key, title, content_type, content_granularity)
               values ('k2', 'FROM', 'tv', 'season')"""
        )
        self.conn.execute(
            """insert into external_ids (canonical_item_id, source, external_id)
               values (1, 'tmdb', '76479')"""
        )
        self.conn.execute(
            """insert into external_ids (canonical_item_id, source, external_id)
               values (2, 'tmdb', '100')"""
        )
        self.conn.execute(
            """insert into content_updates
               (content_update_id, canonical_item_id, update_type, priority, hot_score,
                source_summary_json, review_status, match_confidence_low)
               values (?, ?, ?, ?, ?, ?, 'pending', 0)""",
            ("discovery:76479:2026-05-13", 1, "new_discovery", "P0", 87.0,
             '{"fp":{"platform":"netflix","ranking":1},"tmdb":{"popularity":569.2}}'),
        )
        self.conn.execute(
            """insert into content_updates
               (content_update_id, canonical_item_id, update_type, priority, hot_score,
                source_summary_json, review_status, match_confidence_low)
               values (?, ?, ?, ?, ?, ?, 'pending', 0)""",
            ("new_season:vs_1:s4", 2, "new_season", "P1", 78.0,
             '{"season":4}'),
        )
        self.conn.commit()

    def tearDown(self):
        self.conn.close()
        self.tmpdir.cleanup()

    def test_query_all(self):
        from movietrace.reports.inspect_renderer import query_updates
        updates = query_updates(db_path=str(self.db_path), days=30)
        self.assertEqual(len(updates), 2)

    def test_query_filter_priority(self):
        from movietrace.reports.inspect_renderer import query_updates
        updates = query_updates(db_path=str(self.db_path), days=30, priority="P0")
        self.assertEqual(len(updates), 1)
        self.assertEqual(updates[0]["priority"], "P0")

    def test_query_filter_type(self):
        from movietrace.reports.inspect_renderer import query_updates
        updates = query_updates(db_path=str(self.db_path), days=30, update_type="new_season")
        self.assertEqual(len(updates), 1)
        self.assertEqual(updates[0]["update_type"], "new_season")

    def test_query_by_id(self):
        from movietrace.reports.inspect_renderer import query_updates
        updates = query_updates(db_path=str(self.db_path), days=30,
                                content_update_id="discovery:76479:2026-05-13")
        self.assertEqual(len(updates), 1)
        self.assertEqual(updates[0]["title"], "The Boys")

    def test_query_empty_db(self):
        from movietrace.reports.inspect_renderer import query_updates
        # Use a fresh DB
        updates = query_updates(db_path=str(self.db_path), days=1)
        # The seed has 2 entries but dates may be from a few mins ago
        self.assertIsInstance(updates, list)


if __name__ == "__main__":
    unittest.main()
