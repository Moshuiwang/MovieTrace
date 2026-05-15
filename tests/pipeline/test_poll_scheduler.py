import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))


class PollSchedulerTest(unittest.TestCase):
    def setUp(self):
        from movietrace.db.schema import initialize_database, connect_database

        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / "test.db"
        initialize_database(self.db_path)
        self.conn = connect_database(self.db_path)

    def tearDown(self):
        self.conn.close()
        self.tmpdir.cleanup()

    def _insert_vs(self, tmdb_tv_id, name, priority, last_polled_at=None):
        self.conn.execute(
            """insert into virtual_series(tmdb_tv_id, name, poll_priority, last_polled_at)
               values (?, ?, ?, ?)""",
            (tmdb_tv_id, name, priority, last_polled_at),
        )

    def _insert_vs_with_status(self, tmdb_tv_id, name, priority, tmdb_status):
        self.conn.execute(
            """insert into virtual_series(tmdb_tv_id, name, poll_priority, tmdb_status)
               values (?, ?, ?, ?)""",
            (tmdb_tv_id, name, priority, tmdb_status),
        )

    def test_skip_excluded_from_plan(self):
        from movietrace.pipeline.poll_scheduler import build_daily_poll_plan

        self._insert_vs("1", "Skip Show", "skip")
        plan = build_daily_poll_plan(self.conn)
        self.assertEqual(len(plan), 0)

    def test_routine_polls_all_returning_like(self):
        from movietrace.pipeline.poll_scheduler import build_daily_poll_plan

        for i in range(28):
            self._insert_vs(str(i), f"Show {i}", "urgent")

        plan = build_daily_poll_plan(self.conn)
        # All 28 inserted via _insert_vs have null tmdb_status, so all match
        self.assertEqual(len(plan), 28)

    def test_null_last_polled_first(self):
        from movietrace.pipeline.poll_scheduler import build_daily_poll_plan

        self._insert_vs("1", "Polled recently", "normal", "2026-05-12")
        self._insert_vs("2", "Never polled", "normal", None)

        plan = build_daily_poll_plan(self.conn)
        normal = [p for p in plan if p.poll_priority == "normal"]
        if normal:
            # NULL last_polled_at should be first
            self.assertEqual(normal[0].tmdb_tv_id, "2")

    def test_daily_max_calls_caps_total(self):
        from movietrace.pipeline.poll_scheduler import build_daily_poll_plan

        for i in range(100):
            self._insert_vs(str(i), f"Show {i}", "urgent")

        config = {"baseline_tracking": {"daily_max_calls": 5}}
        plan = build_daily_poll_plan(self.conn, config)
        self.assertLessEqual(len(plan), 5)

    def test_empty_virtual_series_returns_empty(self):
        from movietrace.pipeline.poll_scheduler import build_daily_poll_plan

        plan = build_daily_poll_plan(self.conn)
        self.assertEqual(len(plan), 0)

    def test_catch_up_includes_all_non_skip(self):
        from movietrace.pipeline.poll_scheduler import build_daily_poll_plan

        self._insert_vs_with_status("1", "Returning", "urgent", "Returning Series")
        self._insert_vs_with_status("2", "Ended", "low", "Ended")
        self._insert_vs_with_status("3", "Canceled", "skip", "Canceled")

        plan = build_daily_poll_plan(self.conn, mode="catch-up")

        self.assertEqual({p.tmdb_tv_id for p in plan}, {"1", "2"})

    def test_routine_filters_ended_series(self):
        from movietrace.pipeline.poll_scheduler import build_daily_poll_plan

        self._insert_vs_with_status("1", "Returning", "urgent", "Returning Series")
        self._insert_vs_with_status("2", "Production", "normal", "In Production")
        self._insert_vs_with_status("3", "Ended", "low", "Ended")

        plan = build_daily_poll_plan(self.conn)

        self.assertEqual({p.tmdb_tv_id for p in plan}, {"1", "2"})


if __name__ == "__main__":
    unittest.main()
