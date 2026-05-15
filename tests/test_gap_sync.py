"""Tests for movietrace.feishu.gap_sync — compute_current_gaps.

Uses tempfile + initialize_database to create a real SQLite schema,
then inserts minimal fixture data and verifies gap computation.
No network calls; sync_gap_table is NOT tested here (requires Feishu).
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from movietrace.db.schema import initialize_database, connect_database
from movietrace.feishu.gap_sync import compute_current_gaps


# ── Helpers ──────────────────────────────────────────────────────────────────

def _insert_vs(conn, vs_id: int, tmdb_tv_id: int, name: str,
               poll_priority: str = "urgent",
               tmdb_status: str = "Returning Series") -> None:
    conn.execute(
        """INSERT INTO virtual_series
           (id, tmdb_tv_id, name, tmdb_status, tmdb_number_of_seasons,
            local_max_season, poll_priority)
           VALUES (?, ?, ?, ?, 0, 0, ?)""",
        (vs_id, tmdb_tv_id, name, tmdb_status, poll_priority),
    )


def _insert_upstream_program(conn, prog_id: int) -> None:
    conn.execute(
        """INSERT INTO upstream_programs (id, name, online_flag)
           VALUES (?, 'dummy', '1')""",
        (prog_id,),
    )


def _insert_canonical_item(conn, ci_id: int, vs_id: int, season: int,
                            content_type: str = "tv") -> None:
    conn.execute(
        """INSERT INTO canonical_items
           (id, canonical_item_key, title, content_type, content_granularity,
            virtual_series_id, season_number)
           VALUES (?, ?, 'dummy', ?, 'season', ?, ?)""",
        (ci_id, f"ci_key_{ci_id}", content_type, vs_id, season),
    )


def _insert_external_id_upstream(conn, ci_id: int, prog_id: int) -> None:
    conn.execute(
        """INSERT INTO external_ids (canonical_item_id, source, external_id)
           VALUES (?, 'upstream', ?)""",
        (ci_id, str(prog_id)),
    )


def _insert_api_cache(conn, tmdb_tv_id: int, aired_season: int) -> None:
    """Insert a minimal TMDb detail cache entry with last_episode_to_air."""
    response = {"last_episode_to_air": {"season_number": aired_season}}
    conn.execute(
        """INSERT OR REPLACE INTO api_cache
           (source, cache_key, response_json, fetched_at, expires_at)
           VALUES ('tmdb', ?, ?, datetime('now'), datetime('now', '+1 day'))""",
        (f"tmdb:detail:{tmdb_tv_id}:tv", json.dumps(response)),
    )


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestComputeCurrentGaps(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / "test.db"
        initialize_database(self.db_path)
        self.conn = connect_database(self.db_path)

    def tearDown(self):
        self.conn.close()
        self.tmpdir.cleanup()

    def test_compute_gaps_basic(self):
        """vs with A库 S3 and TMDb last aired S5 → gap_count=2, gap_seasons='S4,S5'."""
        vs_id, tmdb_id = 1, 12345

        _insert_vs(self.conn, vs_id, tmdb_id, "Test Show")
        # A库: seasons 1, 2, 3 (S3 is max)
        for season in [1, 2, 3]:
            prog_id = 100 + season
            ci_id = 200 + season
            _insert_upstream_program(self.conn, prog_id)
            _insert_canonical_item(self.conn, ci_id, vs_id, season)
            _insert_external_id_upstream(self.conn, ci_id, prog_id)
        # TMDb: last aired S5
        _insert_api_cache(self.conn, tmdb_id, 5)
        self.conn.commit()

        rows = compute_current_gaps(self.conn)

        self.assertEqual(len(rows), 1, f"Expected 1 gap row, got {len(rows)}")
        row = rows[0]
        self.assertEqual(row["vs_id"], vs_id)
        self.assertEqual(row["a_lib_max"], 3)
        self.assertEqual(row["tmdb_aired_season"], 5)
        self.assertEqual(row["gap_count"], 2)
        self.assertEqual(row["gap_seasons"], "S4,S5")
        self.assertEqual(row["tmdb_tv_id"], "12345")

    def test_compute_gaps_no_gap_excluded(self):
        """vs with A库 S5 and TMDb S5 → gap_count=0 → excluded from results."""
        vs_id, tmdb_id = 2, 22222

        _insert_vs(self.conn, vs_id, tmdb_id, "Caught Up Show")
        for season in [1, 2, 3, 4, 5]:
            prog_id = 200 + season
            ci_id = 300 + season
            _insert_upstream_program(self.conn, prog_id)
            _insert_canonical_item(self.conn, ci_id, vs_id, season)
            _insert_external_id_upstream(self.conn, ci_id, prog_id)
        _insert_api_cache(self.conn, tmdb_id, 5)
        self.conn.commit()

        rows = compute_current_gaps(self.conn)

        self.assertEqual(len(rows), 0, f"Expected 0 gap rows, got {len(rows)}: {rows}")

    def test_compute_gaps_skip_priority_excluded(self):
        """vs with poll_priority='skip' → excluded even if gap > 0."""
        vs_id, tmdb_id = 3, 33333

        _insert_vs(self.conn, vs_id, tmdb_id, "Skipped Show", poll_priority="skip")
        prog_id, ci_id = 400, 500
        _insert_upstream_program(self.conn, prog_id)
        _insert_canonical_item(self.conn, ci_id, vs_id, 1)
        _insert_external_id_upstream(self.conn, ci_id, prog_id)
        _insert_api_cache(self.conn, tmdb_id, 5)
        self.conn.commit()

        rows = compute_current_gaps(self.conn)

        self.assertEqual(len(rows), 0, f"Expected 0 gap rows for skip vs, got {len(rows)}: {rows}")

    def test_compute_gaps_no_upstream_link_counts_as_zero(self):
        """vs with canonical_item but no upstream external_id → A库 max = 0."""
        vs_id, tmdb_id = 4, 44444

        _insert_vs(self.conn, vs_id, tmdb_id, "Unlinked Show")
        # canonical_item exists but NO external_id → a_lib_max = 0
        _insert_canonical_item(self.conn, 600, vs_id, 3)
        _insert_api_cache(self.conn, tmdb_id, 3)
        self.conn.commit()

        # gap = 3 - 0 = 3
        rows = compute_current_gaps(self.conn)

        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["a_lib_max"], 0)
        self.assertEqual(row["gap_count"], 3)
        self.assertEqual(row["gap_seasons"], "S1,S2,S3")

    def test_compute_gaps_no_api_cache_excluded(self):
        """vs with no api_cache entry → tmdb_aired_season IS NULL → excluded."""
        vs_id, tmdb_id = 5, 55555

        _insert_vs(self.conn, vs_id, tmdb_id, "No Cache Show")
        prog_id, ci_id = 700, 800
        _insert_upstream_program(self.conn, prog_id)
        _insert_canonical_item(self.conn, ci_id, vs_id, 1)
        _insert_external_id_upstream(self.conn, ci_id, prog_id)
        # No api_cache insert
        self.conn.commit()

        rows = compute_current_gaps(self.conn)

        self.assertEqual(len(rows), 0, f"Expected 0 rows when no TMDb cache, got {len(rows)}: {rows}")

    def test_compute_gaps_ordering(self):
        """Two virtual_series with different hot_scores and gap_counts → ordered by hot_score DESC, gap_count DESC."""
        # vs A: hot_score=10, gap_count=1 (a_lib=4, tmdb=5)
        vs_a_id, tmdb_a = 10, 10001
        _insert_vs(self.conn, vs_a_id, tmdb_a, "High Hot Show")
        for season in [1, 2, 3, 4]:
            prog_id = 1000 + season
            ci_id = 2000 + season
            _insert_upstream_program(self.conn, prog_id)
            _insert_canonical_item(self.conn, ci_id, vs_a_id, season)
            _insert_external_id_upstream(self.conn, ci_id, prog_id)
        _insert_api_cache(self.conn, tmdb_a, 5)

        # Add a content_update for hot_score of vs A (hot_score=10)
        self.conn.execute(
            """INSERT INTO canonical_items
               (id, canonical_item_key, title, content_type, content_granularity,
                virtual_series_id, season_number)
               VALUES (?, ?, 'dummy_cu', 'tv', 'season', ?, 5)""",
            (3000, "ci_key_3000", vs_a_id),
        )
        self.conn.execute(
            """INSERT INTO content_updates
               (content_update_id, canonical_item_id, update_type, hot_score, created_at)
               VALUES (?, ?, 'new_season', 10.0, datetime('now', '-1 day'))""",
            ("cu_ordering_a", 3000),
        )

        # vs B: hot_score=5, gap_count=3 (a_lib=1, tmdb=4)
        vs_b_id, tmdb_b = 11, 10002
        _insert_vs(self.conn, vs_b_id, tmdb_b, "Low Hot Show")
        prog_id_b, ci_id_b = 1010, 2010
        _insert_upstream_program(self.conn, prog_id_b)
        _insert_canonical_item(self.conn, ci_id_b, vs_b_id, 1)
        _insert_external_id_upstream(self.conn, ci_id_b, prog_id_b)
        _insert_api_cache(self.conn, tmdb_b, 4)

        self.conn.execute(
            """INSERT INTO canonical_items
               (id, canonical_item_key, title, content_type, content_granularity,
                virtual_series_id, season_number)
               VALUES (?, ?, 'dummy_cu_b', 'tv', 'season', ?, 4)""",
            (3001, "ci_key_3001", vs_b_id),
        )
        self.conn.execute(
            """INSERT INTO content_updates
               (content_update_id, canonical_item_id, update_type, hot_score, created_at)
               VALUES (?, ?, 'new_season', 5.0, datetime('now', '-1 day'))""",
            ("cu_ordering_b", 3001),
        )

        self.conn.commit()

        rows = compute_current_gaps(self.conn)

        # Both should appear (gap > 0, not skipped)
        self.assertGreaterEqual(len(rows), 2, f"Expected at least 2 gap rows, got {len(rows)}: {rows}")

        # Find our two rows
        row_a = next((r for r in rows if r["vs_id"] == vs_a_id), None)
        row_b = next((r for r in rows if r["vs_id"] == vs_b_id), None)
        self.assertIsNotNone(row_a, "vs_a not found in results")
        self.assertIsNotNone(row_b, "vs_b not found in results")

        # vs A has higher hot_score → should appear before vs B
        idx_a = rows.index(row_a)
        idx_b = rows.index(row_b)
        self.assertLess(idx_a, idx_b,
                        f"Expected high-hot-score row (idx={idx_a}) before low-hot-score row (idx={idx_b})")
