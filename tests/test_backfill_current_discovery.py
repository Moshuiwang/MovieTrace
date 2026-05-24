"""Tests for legacy discovery backfill script (p1_57_backfill_current_discovery.py)."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))


def _make_db_with_data():
    """Create a temporary DB with content_updates test data."""
    from movietrace.db.schema import initialize_database, connect_database

    d = tempfile.mkdtemp()
    db_path = Path(d) / "test_backfill.db"
    initialize_database(db_path)
    conn = connect_database(db_path)

    # Insert canonical_items for test content
    conn.execute(
        """INSERT INTO canonical_items
           (canonical_item_key, title, content_type, content_granularity)
           VALUES (?, ?, ?, ?)""",
        ("tmdb:movie:100", "Test Movie", "movie", "movie"),
    )
    conn.execute(
        """INSERT INTO external_ids (canonical_item_id, source, external_id)
           VALUES (1, 'tmdb', 'movie:100')""",
    )
    conn.execute(
        """INSERT INTO canonical_items
           (canonical_item_key, title, original_title, title_zh, content_type, content_granularity)
           VALUES (?, ?, ?, ?, ?, ?)""",
        ("tmdb:tv:200", "Test Show", "Test Show Orig", "测试剧", "tv", "season"),
    )
    conn.execute(
        """INSERT INTO external_ids (canonical_item_id, source, external_id)
           VALUES (2, 'tmdb', 'tv:200')""",
    )

    summary = json.dumps({"fp": {"ranking": 5}}, ensure_ascii=False)

    # Multiple days for TV show
    conn.execute(
        """INSERT INTO content_updates
           (content_update_id, canonical_item_id, update_type, priority, hot_score, source_summary_json)
           VALUES (?, 2, 'new_discovery', 'P1', 65.0, ?)""",
        ("discovery:tv:200:2026-01-01", summary),
    )
    conn.execute(
        """INSERT INTO content_updates
           (content_update_id, canonical_item_id, update_type, priority, hot_score, source_summary_json)
           VALUES (?, 2, 'new_discovery', 'P1', 70.0, ?)""",
        ("discovery:tv:200:2026-01-02", summary),
    )
    conn.execute(
        """INSERT INTO content_updates
           (content_update_id, canonical_item_id, update_type, priority, hot_score, source_summary_json)
           VALUES (?, 2, 'new_discovery', 'P2', 55.0, ?)""",
        ("discovery:tv:200:2026-01-03", summary),
    )

    # Single day for movie
    conn.execute(
        """INSERT INTO content_updates
           (content_update_id, canonical_item_id, update_type, priority, hot_score, source_summary_json)
           VALUES (?, 1, 'new_discovery', 'P2', 52.0, ?)""",
        ("discovery:movie:100:2026-01-15", summary),
    )

    # new_season row (should NOT be backfilled)
    conn.execute(
        """INSERT INTO content_updates
           (content_update_id, canonical_item_id, update_type, priority, hot_score)
           VALUES ('new_season:tv:200:2026-01-10', 2, 'new_season', 'P1', 80.0)""",
    )

    # Invalid content_update_id (should be skipped)
    conn.execute(
        """INSERT INTO content_updates
           (content_update_id, canonical_item_id, update_type, priority, hot_score)
           VALUES ('discovery:unknown_type:999:2026-01-01', 1, 'new_discovery', 'P3', 40.0)""",
    )

    conn.commit()
    return conn, db_path, d


class TestBackfillDryRun(unittest.TestCase):
    def setUp(self):
        self.conn, self.db_path, self._tmpdir = _make_db_with_data()
        self.conn.close()

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmpdir)

    def test_dry_run_does_not_modify_database(self):
        from p1_57_backfill_current_discovery import run_backfill

        stats = run_backfill(self.db_path, commit=False)

        from movietrace.db.schema import connect_database
        conn = connect_database(self.db_path)
        try:
            count = conn.execute(
                "SELECT count(*) FROM current_discovery_items"
            ).fetchone()[0]
            self.assertEqual(count, 0, "dry-run should not write current_discovery_items")
            obs_count = conn.execute(
                "SELECT count(*) FROM discovery_observations"
            ).fetchone()[0]
            self.assertEqual(obs_count, 0, "dry-run should not write discovery_observations")
        finally:
            conn.close()

    def test_dry_run_reports_accurate_stats(self):
        from p1_57_backfill_current_discovery import run_backfill

        stats = run_backfill(self.db_path, commit=False)

        # TV (200) has 3 days, movie (100) has 1 day, invalid 1 → skipped
        self.assertEqual(stats["rows_read"], 5)  # 3 tv + 1 movie + 1 invalid, NOT new_season
        self.assertEqual(stats["current_items_created"], 2)  # tv:200 + movie:100
        self.assertEqual(stats["observations_written"], 4)  # 3 tv + 1 movie
        self.assertEqual(stats["observations_skipped_parse_error"], 1)


class TestBackfillCommit(unittest.TestCase):
    def setUp(self):
        self.conn, self.db_path, self._tmpdir = _make_db_with_data()
        self.conn.close()

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmpdir)

    def _run_commit(self):
        from p1_57_backfill_current_discovery import run_backfill
        return run_backfill(self.db_path, commit=True)

    def test_commit_creates_current_items(self):
        self._run_commit()

        from movietrace.db.schema import connect_database
        conn = connect_database(self.db_path)
        try:
            count = conn.execute("SELECT count(*) FROM current_discovery_items").fetchone()[0]
            self.assertEqual(count, 2)  # tv:200 + movie:100
        finally:
            conn.close()

    def test_commit_tv_show_correct_dates_and_count(self):
        self._run_commit()

        from movietrace.db.schema import connect_database
        conn = connect_database(self.db_path)
        try:
            row = conn.execute(
                "SELECT first_discovered_date, last_discovered_date, discovery_count "
                "FROM current_discovery_items WHERE discovery_key='discovery:tv:200'"
            ).fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row[0], "2026-01-01")
            self.assertEqual(row[1], "2026-01-03")
            self.assertEqual(row[2], 3)
        finally:
            conn.close()

    def test_commit_creates_observations(self):
        self._run_commit()

        from movietrace.db.schema import connect_database
        conn = connect_database(self.db_path)
        try:
            count = conn.execute(
                "SELECT count(*) FROM discovery_observations WHERE discovery_key='discovery:tv:200'"
            ).fetchone()[0]
            self.assertEqual(count, 3)  # 3 unique dates
        finally:
            conn.close()

    def test_commit_new_season_not_backfilled(self):
        self._run_commit()

        from movietrace.db.schema import connect_database
        conn = connect_database(self.db_path)
        try:
            # new_season row should still be in content_updates
            row = conn.execute(
                "SELECT count(*) FROM content_updates WHERE update_type='new_season'"
            ).fetchone()
            self.assertEqual(row[0], 1)
            # No current discovery item for new_season-only IDs
            row2 = conn.execute(
                "SELECT count(*) FROM discovery_observations WHERE observed_date='2026-01-10'"
            ).fetchone()
            self.assertEqual(row2[0], 0)
        finally:
            conn.close()

    def test_commit_idempotent_repeat_run(self):
        self._run_commit()
        stats2 = self._run_commit()

        from movietrace.db.schema import connect_database
        conn = connect_database(self.db_path)
        try:
            count = conn.execute("SELECT count(*) FROM current_discovery_items").fetchone()[0]
            self.assertEqual(count, 2, "idempotent: same item count after second run")
            obs_count = conn.execute("SELECT count(*) FROM discovery_observations").fetchone()[0]
            self.assertEqual(obs_count, 4, "idempotent: same observation count after second run")
        finally:
            conn.close()

    def test_commit_content_updates_unchanged(self):
        original_count = None
        from movietrace.db.schema import connect_database
        conn = connect_database(self.db_path)
        try:
            original_count = conn.execute("SELECT count(*) FROM content_updates").fetchone()[0]
        finally:
            conn.close()

        self._run_commit()

        conn = connect_database(self.db_path)
        try:
            after_count = conn.execute("SELECT count(*) FROM content_updates").fetchone()[0]
            self.assertEqual(after_count, original_count, "content_updates must not be modified")
        finally:
            conn.close()

    def test_commit_skips_invalid_ids(self):
        stats = self._run_commit()
        self.assertEqual(stats["observations_skipped_parse_error"], 1)

    def test_commit_stats_p142_cutoff(self):
        stats = self._run_commit()
        # All test dates are in 2026-01 which is after P142 cutoff (2026-05-22)
        # So observations_before_p142_cutoff should be 0 (all dates < cutoff)
        # Wait: 2026-01-01 < 2026-05-22, so these ARE before cutoff
        self.assertEqual(stats["observations_before_p142_cutoff"], 4)
        self.assertEqual(stats["observations_after_p142_cutoff"], 0)


class TestParseDiscoveryId(unittest.TestCase):
    def test_valid_movie_id(self):
        from p1_57_backfill_current_discovery import _parse_discovery_id
        result = _parse_discovery_id("discovery:movie:12345:2024-01-15")
        self.assertEqual(result, ("movie", "12345", "2024-01-15"))

    def test_valid_tv_id(self):
        from p1_57_backfill_current_discovery import _parse_discovery_id
        result = _parse_discovery_id("discovery:tv:67890:2024-03-01")
        self.assertEqual(result, ("tv", "67890", "2024-03-01"))

    def test_invalid_type_returns_none(self):
        from p1_57_backfill_current_discovery import _parse_discovery_id
        self.assertIsNone(_parse_discovery_id("discovery:show:100:2024-01-01"))

    def test_missing_date_returns_none(self):
        from p1_57_backfill_current_discovery import _parse_discovery_id
        self.assertIsNone(_parse_discovery_id("discovery:tv:100"))

    def test_non_numeric_tmdb_returns_none(self):
        from p1_57_backfill_current_discovery import _parse_discovery_id
        self.assertIsNone(_parse_discovery_id("discovery:tv:abc:2024-01-01"))

    def test_empty_string_returns_none(self):
        from p1_57_backfill_current_discovery import _parse_discovery_id
        self.assertIsNone(_parse_discovery_id(""))

    def test_new_stable_key_returns_none(self):
        # New stable key format (no date) should not parse
        from p1_57_backfill_current_discovery import _parse_discovery_id
        self.assertIsNone(_parse_discovery_id("discovery:tv:100"))


class TestBackfillPerItemCommit(unittest.TestCase):
    """A1: Regression tests for per-item commit strategy.

    Strategy: per-item commit — each item is committed immediately after processing.
    An exception in item N does not affect items 1..(N-1) which are already committed.
    Processing continues for item N+1 onward.
    """

    def _make_db_three_items(self):
        """DB with 3 distinct discovery items (3 unique content_update_ids / dkeys)."""
        from movietrace.db.schema import initialize_database, connect_database

        d = tempfile.mkdtemp()
        db_path = Path(d) / "test_per_item.db"
        initialize_database(db_path)
        conn = connect_database(db_path)

        # Insert canonical_items for 3 movies
        for i in range(1, 4):
            conn.execute(
                """INSERT INTO canonical_items
                   (canonical_item_key, title, content_type, content_granularity)
                   VALUES (?, ?, ?, ?)""",
                (f"tmdb:movie:{i * 100}", f"Movie {i}", "movie", "movie"),
            )
            conn.execute(
                """INSERT INTO external_ids (canonical_item_id, source, external_id)
                   VALUES (?, 'tmdb', ?)""",
                (i, f"movie:{i * 100}"),
            )

        summary = '{"fp": {"ranking": 1}}'
        for i in range(1, 4):
            conn.execute(
                """INSERT INTO content_updates
                   (content_update_id, canonical_item_id, update_type, priority, hot_score, source_summary_json)
                   VALUES (?, ?, 'new_discovery', 'P2', 60.0, ?)""",
                (f"discovery:movie:{i * 100}:2026-01-0{i}", i, summary),
            )
        conn.commit()
        return conn, db_path, d

    def test_midway_failure_items_before_N_are_persisted(self):
        """Per-item commit: items 1 and 2 are committed before item 3 raises;
        DB should have 2 committed items and 1 error after backfill finishes."""
        conn, db_path, d = self._make_db_three_items()
        conn.close()

        class PatchedConn:
            """Wrap a real connection, raise on the 3rd current_discovery_items INSERT."""
            def __init__(self, real):
                self._real = real
                self._insert_count = 0

            def execute(self, sql, params=()):
                if "INSERT INTO current_discovery_items" in sql:
                    self._insert_count += 1
                    if self._insert_count == 3:
                        raise RuntimeError("Simulated failure on item 3")
                return self._real.execute(sql, params)

            def commit(self):
                return self._real.commit()

            def rollback(self):
                return self._real.rollback()

            def close(self):
                return self._real.close()

            def __getattr__(self, name):
                return getattr(self._real, name)

        from unittest.mock import patch as _patch
        from movietrace.db.schema import connect_database as _real_cd

        def fake_connect(db_path_arg):
            return PatchedConn(_real_cd(db_path_arg))

        # Patch the import target inside the module where run_backfill actually calls it.
        # Note: save the real function before patching to avoid recursion.
        with _patch("movietrace.db.schema.connect_database", side_effect=fake_connect):
            from p1_57_backfill_current_discovery import run_backfill
            stats = run_backfill(db_path, commit=True)

        # Per-item commit: items 1 and 2 are already committed; item 3 failed
        self.assertEqual(stats["errors"], 1)
        self.assertEqual(stats["current_items_created"], 2)

        verify_conn = _real_cd(db_path)
        try:
            count = verify_conn.execute(
                "SELECT count(*) FROM current_discovery_items"
            ).fetchone()[0]
            # Items 1 and 2 must be persisted even though item 3 failed
            self.assertGreaterEqual(count, 2, "Per-item commit: items before failure must be persisted")
        finally:
            verify_conn.close()

        import shutil
        shutil.rmtree(d)

    def test_stats_errors_incremented_on_per_item_failure(self):
        """A1: stats['errors'] counts failed items; successful items are counted normally."""
        conn, db_path, d = self._make_db_three_items()
        conn.close()

        from unittest.mock import patch as _patch

        class PatchedConn2:
            def __init__(self, real):
                self._real = real
                self._insert_count = 0

            def execute(self, sql, params=()):
                if "INSERT INTO current_discovery_items" in sql:
                    self._insert_count += 1
                    if self._insert_count == 2:
                        raise RuntimeError("Simulated failure on item 2")
                return self._real.execute(sql, params)

            def commit(self):
                return self._real.commit()

            def rollback(self):
                return self._real.rollback()

            def close(self):
                return self._real.close()

            def __getattr__(self, name):
                return getattr(self._real, name)

        from movietrace.db.schema import connect_database as _real_cd2

        def fake_connect2(db_path_arg):
            return PatchedConn2(_real_cd2(db_path_arg))

        with _patch("movietrace.db.schema.connect_database", side_effect=fake_connect2):
            from p1_57_backfill_current_discovery import run_backfill
            stats = run_backfill(db_path, commit=True)

        # Items 1 and 3 succeed, item 2 fails
        self.assertEqual(stats["errors"], 1)
        self.assertEqual(stats["current_items_created"], 2)

        import shutil
        shutil.rmtree(d)


if __name__ == "__main__":
    unittest.main()
