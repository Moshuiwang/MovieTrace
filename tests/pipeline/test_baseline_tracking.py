import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))


class MockTmdbDetailClient:
    def __init__(self, details_by_id=None):
        self.details = details_by_id or {}
        self.call_count = 0

    def get_tv_details(self, tmdb_tv_id):
        self.call_count += 1
        return self.details.get(tmdb_tv_id, {})


class BaselineTrackingTest(unittest.TestCase):
    def setUp(self):
        from movietrace.db.schema import initialize_database, connect_database

        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / "test.db"
        initialize_database(self.db_path)
        self.conn = connect_database(self.db_path)

    def tearDown(self):
        self.conn.close()
        self.tmpdir.cleanup()

    def _setup_series(self, tmdb_tv_id="1399", name="Test Show", local_max=1):
        self.conn.execute(
            """insert into virtual_series(tmdb_tv_id, name, poll_priority,
               tmdb_number_of_seasons, local_max_season)
               values (?, ?, 'normal', 8, ?)""",
            (tmdb_tv_id, name, local_max),
        )
        vs_id = self.conn.execute("select last_insert_rowid()").fetchone()[0]

        # Create a season-level canonical_item
        self.conn.execute(
            """insert into canonical_items(
                canonical_item_key, title, content_type, content_granularity,
                season_number, virtual_series_id
            ) values (?, ?, 'tv', 'season', 1, ?)""",
            (f"tmdb:tv:{tmdb_tv_id}:season:1", f"{name} S01", vs_id),
        )
        ci_id = self.conn.execute("select last_insert_rowid()").fetchone()[0]
        self.conn.execute(
            """insert or ignore into external_ids(
                canonical_item_id, source, external_id, external_granularity
            ) values (?, 'tmdb', ?, 'series')""",
            (ci_id, tmdb_tv_id),
        )
        return vs_id, ci_id

    def test_detect_new_season_simple(self):
        from movietrace.pipeline.baseline_tracking import detect_new_seasons
        from movietrace.pipeline.poll_scheduler import PollPlan

        vs_id, _ = self._setup_series(tmdb_tv_id="1399", name="Test Show", local_max=1)

        plan = [
            PollPlan(
                virtual_series_id=vs_id,
                tmdb_tv_id="1399",
                name="Test Show",
                poll_priority="normal",
                last_polled_at=None,
            )
        ]
        mock = MockTmdbDetailClient(
            {"1399": {"name": "Test Show", "status": "Returning Series", "number_of_seasons": 3}}
        )

        events = detect_new_seasons(self.conn, plan, mock, interval=0)
        self.assertEqual(len(events), 2)  # seasons 2 and 3
        self.assertEqual(events[0].new_season_number, 2)
        self.assertEqual(events[1].new_season_number, 3)

    def test_no_new_season_returns_empty(self):
        from movietrace.pipeline.baseline_tracking import detect_new_seasons
        from movietrace.pipeline.poll_scheduler import PollPlan

        vs_id, _ = self._setup_series(tmdb_tv_id="1399", name="Test Show", local_max=8)

        plan = [
            PollPlan(
                virtual_series_id=vs_id,
                tmdb_tv_id="1399",
                name="Test Show",
                poll_priority="normal",
                last_polled_at=None,
            )
        ]
        mock = MockTmdbDetailClient(
            {"1399": {"name": "Test Show", "status": "Ended", "number_of_seasons": 8}}
        )

        events = detect_new_seasons(self.conn, plan, mock, interval=0)
        self.assertEqual(len(events), 0)

    def test_tmdb_api_error_skips_gracefully(self):
        from movietrace.pipeline.baseline_tracking import detect_new_seasons
        from movietrace.pipeline.poll_scheduler import PollPlan

        vs_id, _ = self._setup_series(tmdb_tv_id="99999", name="Error Show", local_max=0)

        plan = [
            PollPlan(
                virtual_series_id=vs_id,
                tmdb_tv_id="99999",
                name="Error Show",
                poll_priority="normal",
                last_polled_at=None,
            )
        ]

        class ErrorClient:
            def get_tv_details(self, tmdb_tv_id):
                raise RuntimeError("API down")

        events = detect_new_seasons(self.conn, plan, ErrorClient(), interval=0)
        self.assertEqual(len(events), 0)

    def test_write_content_updates_fields(self):
        from movietrace.pipeline.baseline_tracking import (
            NewSeasonEvent,
            write_content_updates,
        )

        vs_id, ci_id = self._setup_series(tmdb_tv_id="1399", name="Test Show", local_max=1)

        events = [
            NewSeasonEvent(
                virtual_series_id=vs_id,
                tmdb_tv_id="1399",
                name="Test Show",
                new_season_number=2,
                previous_local_max=1,
                detected_at="2026-05-12 12:00:00 +08",
            )
        ]
        written = write_content_updates(self.conn, events)
        self.assertEqual(written, 1)

        row = self.conn.execute(
            """select update_type, hot_score, match_confidence_low, priority,
                      source_summary_json
               from content_updates where update_type = 'new_season'"""
        ).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row[0], "new_season")
        self.assertIsNotNone(row[1])
        self.assertEqual(row[2], 0)  # match_confidence_low = 0
        import json

        summary = json.loads(row[4])
        self.assertEqual(summary["baseline_detected_at"], "2026-05-12 12:00:00 +08")
        self.assertEqual(summary["baseline_local_max_season"], 1)

    def test_detect_new_season_reuses_tmdb_detail_cache(self):
        from movietrace.pipeline.baseline_tracking import detect_new_seasons
        from movietrace.pipeline.poll_scheduler import PollPlan
        import json

        vs_id, _ = self._setup_series(tmdb_tv_id="1399", name="Test Show", local_max=1)
        self.conn.execute(
            """insert into api_cache(source, cache_key, response_json)
               values ('tmdb', 'tmdb:detail:1399:tv', ?)""",
            (json.dumps({
                "name": "Test Show",
                "status": "Returning Series",
                "number_of_seasons": 2,
                "popularity": 500,
                "vote_average": 8,
                "vote_count": 1000,
                "original_language": "en",
            }),),
        )
        self.conn.commit()
        plan = [
            PollPlan(
                virtual_series_id=vs_id,
                tmdb_tv_id="1399",
                name="Test Show",
                poll_priority="normal",
                last_polled_at=None,
            )
        ]
        mock = MockTmdbDetailClient({})

        events = detect_new_seasons(self.conn, plan, mock, interval=0)

        self.assertEqual(mock.call_count, 0)
        self.assertEqual(len(events), 1)
        self.assertGreater(events[0].hot_score, 0)

    def test_write_content_updates_dedup(self):
        from movietrace.pipeline.baseline_tracking import (
            NewSeasonEvent,
            write_content_updates,
        )

        vs_id, ci_id = self._setup_series(tmdb_tv_id="1399", name="Test Show", local_max=1)

        events = [
            NewSeasonEvent(
                virtual_series_id=vs_id,
                tmdb_tv_id="1399",
                name="Test Show",
                new_season_number=2,
                previous_local_max=1,
                detected_at="2026-05-12 12:00:00 +08",
            )
        ]
        written1 = write_content_updates(self.conn, events)
        written2 = write_content_updates(self.conn, events)
        self.assertEqual(written1, 1)
        self.assertEqual(written2, 0)  # Same content_update_id → deduped

    def test_write_content_updates_merges_multi_season(self):
        """P1.12-E: Multiple new seasons for same series merge into one row."""
        from movietrace.pipeline.baseline_tracking import (
            NewSeasonEvent,
            write_content_updates,
        )
        import json

        vs_id, ci_id = self._setup_series(tmdb_tv_id="1399", name="Test Show", local_max=1)

        events = [
            NewSeasonEvent(
                virtual_series_id=vs_id,
                tmdb_tv_id="1399",
                name="Test Show",
                new_season_number=2,
                previous_local_max=1,
                detected_at="2026-05-12 12:00:00 +08",
            ),
            NewSeasonEvent(
                virtual_series_id=vs_id,
                tmdb_tv_id="1399",
                name="Test Show",
                new_season_number=3,
                previous_local_max=1,
                detected_at="2026-05-12 12:00:00 +08",
            ),
        ]
        written = write_content_updates(self.conn, events)
        self.assertEqual(written, 1)  # Merged into one row

        row = self.conn.execute(
            """select content_update_id, source_summary_json
               from content_updates where update_type = 'new_season'"""
        ).fetchone()
        self.assertIsNotNone(row)
        # content_update_id reflects range
        self.assertIn("s2-s3", row[0])
        summary = json.loads(row[1])
        self.assertEqual(summary["season"], 3)  # backward compat: max
        self.assertEqual(summary["seasons"], [2, 3])
        self.assertEqual(summary["season_min"], 2)
        self.assertEqual(summary["season_max"], 3)
        self.assertEqual(summary["baseline_local_max_season"], 1)

    def test_write_content_updates_single_season_still_works(self):
        """Single new season: backward-compatible summary with season field."""
        from movietrace.pipeline.baseline_tracking import (
            NewSeasonEvent,
            write_content_updates,
        )
        import json

        vs_id, ci_id = self._setup_series(tmdb_tv_id="1399", name="Test Show", local_max=1)

        events = [
            NewSeasonEvent(
                virtual_series_id=vs_id,
                tmdb_tv_id="1399",
                name="Test Show",
                new_season_number=2,
                previous_local_max=1,
                detected_at="2026-05-12 12:00:00 +08",
            ),
        ]
        written = write_content_updates(self.conn, events)
        self.assertEqual(written, 1)

        row = self.conn.execute(
            """select content_update_id, source_summary_json
               from content_updates where update_type = 'new_season'"""
        ).fetchone()
        summary = json.loads(row[1])
        self.assertEqual(summary["season"], 2)
        self.assertEqual(summary["seasons"], [2])
        self.assertEqual(summary["season_min"], 2)
        self.assertEqual(summary["season_max"], 2)
        # Single season uses simple id
        self.assertIn("s2", row[0])
        self.assertNotIn("-", row[0].split(":")[-1])

    def test_update_local_max_season(self):
        from movietrace.pipeline.baseline_tracking import update_local_max_season

        vs_id, _ = self._setup_series(tmdb_tv_id="1399", name="Test Show", local_max=1)

        update_local_max_season(self.conn, vs_id, 5)

        row = self.conn.execute(
            "select local_max_season from virtual_series where id = ?", (vs_id,)
        ).fetchone()
        self.assertEqual(row[0], 5)


if __name__ == "__main__":
    unittest.main()
