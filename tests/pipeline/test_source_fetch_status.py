import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))


class SourceFetchStatusTest(unittest.TestCase):
    def setUp(self):
        import sqlite3
        from movietrace.db.schema import initialize_database, connect_database

        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / "test_status.db"
        initialize_database(self.db_path)
        self.conn = connect_database(self.db_path)
        self.conn.row_factory = sqlite3.Row

    def tearDown(self):
        self.conn.close()
        self.tmpdir.cleanup()

    def test_record_fresh_status(self):
        from movietrace.pipeline.source_fetch_status import record_source_fetch_run

        record_source_fetch_run(self.conn, "2026-05-14", "tmdb", "fresh",
                                source_snapshot_date="2026-05-14",
                                rows_fetched=60, rows_inserted=55)
        self.conn.commit()

        row = self.conn.execute(
            "select * from source_fetch_runs where target_date=? and source=?",
            ("2026-05-14", "tmdb"),
        ).fetchone()
        self.assertEqual(row["status"], "fresh")
        self.assertEqual(row["source_snapshot_date"], "2026-05-14")
        self.assertEqual(row["rows_fetched"], 60)
        self.assertEqual(row["rows_inserted"], 55)

    def test_record_fallback_status(self):
        from movietrace.pipeline.source_fetch_status import record_source_fetch_run

        record_source_fetch_run(self.conn, "2026-05-14", "flixpatrol", "fallback",
                                source_snapshot_date="2026-05-13",
                                rows_fetched=100, rows_inserted=100)
        self.conn.commit()

        row = self.conn.execute(
            "select * from source_fetch_runs where target_date=? and source=?",
            ("2026-05-14", "flixpatrol"),
        ).fetchone()
        self.assertEqual(row["status"], "fallback")
        self.assertEqual(row["source_snapshot_date"], "2026-05-13")

    def test_record_failed_no_fallback(self):
        from movietrace.pipeline.source_fetch_status import record_source_fetch_run

        record_source_fetch_run(self.conn, "2026-05-14", "trakt", "failed_no_fallback",
                                error_message="Connection timeout")
        self.conn.commit()

        row = self.conn.execute(
            "select * from source_fetch_runs where target_date=? and source=?",
            ("2026-05-14", "trakt"),
        ).fetchone()
        self.assertEqual(row["status"], "failed_no_fallback")
        self.assertIsNone(row["source_snapshot_date"])
        self.assertIsNotNone(row["error_message"])

    def test_upsert_on_duplicate(self):
        from movietrace.pipeline.source_fetch_status import record_source_fetch_run

        record_source_fetch_run(self.conn, "2026-05-14", "tmdb", "fresh",
                                rows_fetched=50)
        self.conn.commit()
        record_source_fetch_run(self.conn, "2026-05-14", "tmdb", "fallback",
                                rows_fetched=0)
        self.conn.commit()

        count = self.conn.execute(
            "select count(*) from source_fetch_runs where target_date=? and source=?",
            ("2026-05-14", "tmdb"),
        ).fetchone()[0]
        self.assertEqual(count, 1)

    def test_invalid_status_raises(self):
        from movietrace.pipeline.source_fetch_status import record_source_fetch_run

        with self.assertRaises(ValueError):
            record_source_fetch_run(self.conn, "2026-05-14", "tmdb", "bad_status")

    def test_invalid_source_raises(self):
        from movietrace.pipeline.source_fetch_status import record_source_fetch_run

        with self.assertRaises(ValueError):
            record_source_fetch_run(self.conn, "2026-05-14", "unknown_source", "fresh")

    def test_get_source_fetch_runs(self):
        from movietrace.pipeline.source_fetch_status import (
            record_source_fetch_run,
            get_source_fetch_runs,
        )

        record_source_fetch_run(self.conn, "2026-05-14", "tmdb", "fresh")
        record_source_fetch_run(self.conn, "2026-05-14", "trakt", "fresh")
        self.conn.commit()

        runs = get_source_fetch_runs(self.conn, target_date="2026-05-14")
        self.assertEqual(len(runs), 2)

        runs_tmdb = get_source_fetch_runs(self.conn, target_date="2026-05-14", source="tmdb")
        self.assertEqual(len(runs_tmdb), 1)
        self.assertEqual(runs_tmdb[0]["source"], "tmdb")

    def test_find_latest_source_snapshot(self):
        from movietrace.pipeline.source_fetch_status import (
            record_source_fetch_run,
            find_latest_source_snapshot,
        )

        # Populate historical runs
        record_source_fetch_run(self.conn, "2026-05-14", "tmdb", "fresh",
                                source_snapshot_date="2026-05-14",
                                rows_fetched=60)
        record_source_fetch_run(self.conn, "2026-05-13", "tmdb", "fresh",
                                source_snapshot_date="2026-05-13",
                                rows_fetched=58)
        record_source_fetch_run(self.conn, "2026-05-12", "tmdb", "fresh",
                                source_snapshot_date="2026-05-12",
                                rows_fetched=55)
        self.conn.commit()

        snapshot = find_latest_source_snapshot(
            self.conn, "tmdb", "2026-05-15", max_staleness_days=30
        )
        self.assertEqual(snapshot, "2026-05-14")

    def test_find_latest_source_snapshot_ignores_beyond_max_staleness(self):
        from movietrace.pipeline.source_fetch_status import (
            record_source_fetch_run,
            find_latest_source_snapshot,
        )

        record_source_fetch_run(self.conn, "2026-04-01", "tmdb", "fresh",
                                source_snapshot_date="2026-04-01",
                                rows_fetched=30)
        self.conn.commit()

        snapshot = find_latest_source_snapshot(
            self.conn, "tmdb", "2026-05-15", max_staleness_days=30
        )
        self.assertIsNone(snapshot)

    def test_find_latest_source_snapshot_skips_failed(self):
        from movietrace.pipeline.source_fetch_status import (
            record_source_fetch_run,
            find_latest_source_snapshot,
        )

        record_source_fetch_run(self.conn, "2026-05-14", "tmdb", "failed_no_fallback",
                                error_message="API unreachable")
        record_source_fetch_run(self.conn, "2026-05-13", "tmdb", "fresh",
                                source_snapshot_date="2026-05-13",
                                rows_fetched=58)
        self.conn.commit()

        snapshot = find_latest_source_snapshot(
            self.conn, "tmdb", "2026-05-15", max_staleness_days=30
        )
        # Should skip 05-14 (failed) and return 05-13 (fresh)
        self.assertEqual(snapshot, "2026-05-13")



if __name__ == "__main__":
    unittest.main()
