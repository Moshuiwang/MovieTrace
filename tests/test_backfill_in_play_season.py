"""Tests for P1.24-G: backfill_in_play_season script."""

from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

# Add scripts directory to path
SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from p1_24_backfill_in_play_season import (
    _extract_tmdb_tv_id,
    backfill,
)


def _setup_db(conn):
    """Set up minimal schema for testing."""
    conn.executescript(
        """
        create table content_updates (
            id integer primary key autoincrement,
            content_update_id text not null,
            canonical_item_id integer not null,
            update_type text not null,
            priority text,
            hot_score integer,
            source_summary_json text,
            created_at text default current_timestamp
        );
        create table api_cache (
            id integer primary key autoincrement,
            source text not null,
            cache_key text not null,
            response_json text not null,
            fetched_at text default current_timestamp
        );
        create unique index ux_api_cache_source_key
            on api_cache(source, cache_key);
    """
    )


class TestExtractTmdbTvId:
    """Test content_update_id parsing."""

    def test_extract_from_discovery_tv_format(self):
        """discovery:tv:{tmdb_id}:{date} → tmdb_id"""
        result = _extract_tmdb_tv_id("discovery:tv:1416:2026-05-17")
        assert result == "1416"

    def test_extract_from_new_season_format(self):
        """new_season:{tmdb_tv_id}:{season}:{date} → tmdb_tv_id"""
        result = _extract_tmdb_tv_id("new_season:1396:5:2026-05-17")
        assert result == "1396"

    def test_extract_from_movie_returns_none(self):
        """discovery:movie:... → None (movie, not TV)"""
        result = _extract_tmdb_tv_id("discovery:movie:550:2026-05-17")
        assert result is None

    def test_extract_from_malformed_returns_none(self):
        """Malformed strings → None"""
        assert _extract_tmdb_tv_id("") is None
        assert _extract_tmdb_tv_id("invalid") is None
        assert _extract_tmdb_tv_id("discovery:tv") is None
        assert _extract_tmdb_tv_id(None) is None

    def test_extract_with_numeric_id_string(self):
        """Verify ID is returned as string (not converted to int)"""
        result = _extract_tmdb_tv_id("discovery:tv:12345:2026-05-17")
        assert result == "12345"
        assert isinstance(result, str)


class TestBackfillDryRun:
    """Test dry-run mode (no DB writes)."""

    def test_dry_run_on_temp_file(self, tmp_path):
        """dry_run=True on temp file should not modify DB."""
        db_path = str(tmp_path / "test.db")

        conn = sqlite3.connect(db_path)
        _setup_db(conn)

        now = datetime.now(tz=timezone.utc).isoformat()
        conn.execute(
            """insert into content_updates
               (content_update_id, canonical_item_id, update_type, source_summary_json, created_at)
               values (?, ?, ?, ?, ?)""",
            ("discovery:tv:1416:2026-05-17", 1, "new_discovery", "{}", now),
        )

        tmdb_detail = {
            "id": 1416,
            "last_episode_to_air": {"season_number": 22, "episode_number": 5},
        }
        conn.execute(
            """insert into api_cache (source, cache_key, response_json)
               values (?, ?, ?)""",
            ("tmdb", "tmdb:detail:1416:tv", json.dumps(tmdb_detail)),
        )
        conn.commit()
        conn.close()

        # Run dry-run
        stats = backfill(db_path, dry_run=True, days=30, logger=None)
        assert stats["dry_run"] is True
        assert stats["updated"] == 1

        # Verify DB was not modified
        conn = sqlite3.connect(db_path)
        row = conn.execute(
            "select source_summary_json from content_updates where id = 1"
        ).fetchone()
        assert row[0] == "{}"  # unchanged
        conn.close()


class TestBackfillUpdates:
    """Test actual backfill updates."""

    def test_backfill_updates_source_summary_with_last_aired(self, tmp_path):
        """Backfill should merge last_episode_to_air into source_summary."""
        db_path = str(tmp_path / "test.db")

        conn = sqlite3.connect(db_path)
        _setup_db(conn)

        now = datetime.now(tz=timezone.utc).isoformat()
        conn.execute(
            """insert into content_updates
               (content_update_id, canonical_item_id, update_type, source_summary_json, created_at)
               values (?, ?, ?, ?, ?)""",
            ("discovery:tv:1416:2026-05-17", 1, "new_discovery", "{}", now),
        )

        tmdb_detail = {
            "id": 1416,
            "name": "Grey's Anatomy",
            "last_episode_to_air": {"season_number": 22, "episode_number": 5},
        }
        conn.execute(
            """insert into api_cache (source, cache_key, response_json)
               values (?, ?, ?)""",
            ("tmdb", "tmdb:detail:1416:tv", json.dumps(tmdb_detail)),
        )
        conn.commit()
        conn.close()

        # Run backfill
        stats = backfill(db_path, dry_run=False, days=30, logger=None)
        assert stats["updated"] == 1
        assert stats["errors"] == 0

        # Verify update
        conn = sqlite3.connect(db_path)
        row = conn.execute(
            "select source_summary_json from content_updates where id = 1"
        ).fetchone()
        assert row is not None
        summary = json.loads(row[0])
        assert summary.get("last_episode_to_air") == {
            "season_number": 22,
            "episode_number": 5,
        }
        conn.close()

    def test_backfill_preserves_existing_fields(self, tmp_path):
        """Backfill should preserve existing fields in source_summary."""
        db_path = str(tmp_path / "test.db")

        conn = sqlite3.connect(db_path)
        _setup_db(conn)

        now = datetime.now(tz=timezone.utc).isoformat()
        existing_summary = {"imdb_id": "tt0944947", "genres": [18, 10759]}
        conn.execute(
            """insert into content_updates
               (content_update_id, canonical_item_id, update_type, source_summary_json, created_at)
               values (?, ?, ?, ?, ?)""",
            (
                "discovery:tv:1416:2026-05-17",
                1,
                "new_discovery",
                json.dumps(existing_summary),
                now,
            ),
        )

        tmdb_detail = {
            "id": 1416,
            "last_episode_to_air": {"season_number": 22, "episode_number": 5},
        }
        conn.execute(
            """insert into api_cache (source, cache_key, response_json)
               values (?, ?, ?)""",
            ("tmdb", "tmdb:detail:1416:tv", json.dumps(tmdb_detail)),
        )
        conn.commit()
        conn.close()

        stats = backfill(db_path, dry_run=False, days=30, logger=None)
        assert stats["updated"] == 1

        conn = sqlite3.connect(db_path)
        row = conn.execute(
            "select source_summary_json from content_updates where id = 1"
        ).fetchone()
        summary = json.loads(row[0])
        # Existing fields preserved
        assert summary.get("imdb_id") == "tt0944947"
        assert summary.get("genres") == [18, 10759]
        # New field added
        assert summary.get("last_episode_to_air") == {
            "season_number": 22,
            "episode_number": 5,
        }
        conn.close()


class TestBackfillSkips:
    """Test skip conditions."""

    def test_skip_when_cache_missing(self, tmp_path):
        """TV row without matching api_cache → skipped_no_cache."""
        db_path = str(tmp_path / "test.db")

        conn = sqlite3.connect(db_path)
        _setup_db(conn)

        now = datetime.now(tz=timezone.utc).isoformat()
        conn.execute(
            """insert into content_updates
               (content_update_id, canonical_item_id, update_type, source_summary_json, created_at)
               values (?, ?, ?, ?, ?)""",
            ("discovery:tv:9999:2026-05-17", 1, "new_discovery", "{}", now),
        )
        conn.commit()
        conn.close()

        stats = backfill(db_path, dry_run=False, days=30, logger=None)
        assert stats["skipped_no_cache"] == 1
        assert stats["updated"] == 0

    def test_skip_when_already_has_last_aired(self, tmp_path):
        """Row with existing last_episode_to_air → skipped_already_has (idempotent)."""
        db_path = str(tmp_path / "test.db")

        conn = sqlite3.connect(db_path)
        _setup_db(conn)

        now = datetime.now(tz=timezone.utc).isoformat()
        existing_summary = {
            "last_episode_to_air": {"season_number": 21, "episode_number": 10}
        }
        conn.execute(
            """insert into content_updates
               (content_update_id, canonical_item_id, update_type, source_summary_json, created_at)
               values (?, ?, ?, ?, ?)""",
            (
                "discovery:tv:1416:2026-05-17",
                1,
                "new_discovery",
                json.dumps(existing_summary),
                now,
            ),
        )

        tmdb_detail = {
            "id": 1416,
            "last_episode_to_air": {"season_number": 22, "episode_number": 5},
        }
        conn.execute(
            """insert into api_cache (source, cache_key, response_json)
               values (?, ?, ?)""",
            ("tmdb", "tmdb:detail:1416:tv", json.dumps(tmdb_detail)),
        )
        conn.commit()
        conn.close()

        stats = backfill(db_path, dry_run=False, days=30, logger=None)
        assert stats["skipped_already_has"] == 1
        assert stats["updated"] == 0

    def test_skip_movie_rows(self, tmp_path):
        """discovery:movie:... rows should be skipped (not matched by query)."""
        db_path = str(tmp_path / "test.db")

        conn = sqlite3.connect(db_path)
        _setup_db(conn)

        now = datetime.now(tz=timezone.utc).isoformat()
        # Insert both TV and movie
        conn.execute(
            """insert into content_updates
               (content_update_id, canonical_item_id, update_type, source_summary_json, created_at)
               values (?, ?, ?, ?, ?)""",
            ("discovery:movie:550:2026-05-17", 1, "new_discovery", "{}", now),
        )
        conn.execute(
            """insert into content_updates
               (content_update_id, canonical_item_id, update_type, source_summary_json, created_at)
               values (?, ?, ?, ?, ?)""",
            ("discovery:tv:1416:2026-05-17", 2, "new_discovery", "{}", now),
        )

        # Only TV cache
        tmdb_detail = {
            "id": 1416,
            "last_episode_to_air": {"season_number": 22, "episode_number": 5},
        }
        conn.execute(
            """insert into api_cache (source, cache_key, response_json)
               values (?, ?, ?)""",
            ("tmdb", "tmdb:detail:1416:tv", json.dumps(tmdb_detail)),
        )
        conn.commit()
        conn.close()

        stats = backfill(db_path, dry_run=False, days=30, logger=None)
        # Movie row not returned by query, only TV processed
        assert stats["scanned"] == 1  # Only TV from query
        assert stats["updated"] == 1


class TestBackfillErrors:
    """Test error handling."""

    def test_handle_invalid_json_in_cache(self, tmp_path):
        """Invalid JSON in api_cache → errors++, skip row."""
        db_path = str(tmp_path / "test.db")

        conn = sqlite3.connect(db_path)
        _setup_db(conn)

        now = datetime.now(tz=timezone.utc).isoformat()
        conn.execute(
            """insert into content_updates
               (content_update_id, canonical_item_id, update_type, source_summary_json, created_at)
               values (?, ?, ?, ?, ?)""",
            ("discovery:tv:1416:2026-05-17", 1, "new_discovery", "{}", now),
        )

        # Invalid JSON
        conn.execute(
            """insert into api_cache (source, cache_key, response_json)
               values (?, ?, ?)""",
            ("tmdb", "tmdb:detail:1416:tv", "not valid json {["),
        )
        conn.commit()
        conn.close()

        stats = backfill(db_path, dry_run=False, days=30, logger=None)
        assert stats["errors"] == 1
        assert stats["updated"] == 0

    def test_handle_invalid_json_in_source_summary(self, tmp_path):
        """Invalid JSON in source_summary_json → skip, treat as empty."""
        db_path = str(tmp_path / "test.db")

        conn = sqlite3.connect(db_path)
        _setup_db(conn)

        now = datetime.now(tz=timezone.utc).isoformat()
        conn.execute(
            """insert into content_updates
               (content_update_id, canonical_item_id, update_type, source_summary_json, created_at)
               values (?, ?, ?, ?, ?)""",
            ("discovery:tv:1416:2026-05-17", 1, "new_discovery", "invalid json", now),
        )

        tmdb_detail = {
            "id": 1416,
            "last_episode_to_air": {"season_number": 22, "episode_number": 5},
        }
        conn.execute(
            """insert into api_cache (source, cache_key, response_json)
               values (?, ?, ?)""",
            ("tmdb", "tmdb:detail:1416:tv", json.dumps(tmdb_detail)),
        )
        conn.commit()
        conn.close()

        stats = backfill(db_path, dry_run=False, days=30, logger=None)
        # Should treat as empty and update
        assert stats["updated"] == 1
        assert stats["errors"] == 0


class TestBackfillStats:
    """Test stats accumulation."""

    def test_stats_structure(self, tmp_path):
        """Return stats has required fields."""
        db_path = str(tmp_path / "test.db")

        conn = sqlite3.connect(db_path)
        _setup_db(conn)
        conn.close()

        stats = backfill(db_path, dry_run=False, days=30, logger=None)
        required_fields = [
            "scanned",
            "updated",
            "skipped_no_cache",
            "skipped_movie",
            "skipped_already_has",
            "errors",
            "dry_run",
        ]
        for field in required_fields:
            assert field in stats
            assert isinstance(stats[field], (int, bool))

    def test_mixed_scenario(self, tmp_path):
        """Complex scenario: mix of updates, skips, and errors."""
        db_path = str(tmp_path / "test.db")

        conn = sqlite3.connect(db_path)
        _setup_db(conn)

        now = datetime.now(tz=timezone.utc).isoformat()

        # Row 1: Will update
        conn.execute(
            """insert into content_updates
               (content_update_id, canonical_item_id, update_type, source_summary_json, created_at)
               values (?, ?, ?, ?, ?)""",
            ("discovery:tv:1416:2026-05-17", 1, "new_discovery", "{}", now),
        )

        # Row 2: Will skip - already has last_episode_to_air
        conn.execute(
            """insert into content_updates
               (content_update_id, canonical_item_id, update_type, source_summary_json, created_at)
               values (?, ?, ?, ?, ?)""",
            (
                "discovery:tv:1396:2026-05-17",
                2,
                "new_discovery",
                json.dumps({"last_episode_to_air": {"season_number": 5}}),
                now,
            ),
        )

        # Row 3: Will skip - no cache
        conn.execute(
            """insert into content_updates
               (content_update_id, canonical_item_id, update_type, source_summary_json, created_at)
               values (?, ?, ?, ?, ?)""",
            ("discovery:tv:9999:2026-05-17", 3, "new_discovery", "{}", now),
        )

        # Cache for row 1
        tmdb_detail = {
            "id": 1416,
            "last_episode_to_air": {"season_number": 22, "episode_number": 5},
        }
        conn.execute(
            """insert into api_cache (source, cache_key, response_json)
               values (?, ?, ?)""",
            ("tmdb", "tmdb:detail:1416:tv", json.dumps(tmdb_detail)),
        )

        # Cache for row 2 (but row already has data, so skip)
        cache2 = {
            "id": 1396,
            "last_episode_to_air": {"season_number": 6, "episode_number": 1},
        }
        conn.execute(
            """insert into api_cache (source, cache_key, response_json)
               values (?, ?, ?)""",
            ("tmdb", "tmdb:detail:1396:tv", json.dumps(cache2)),
        )

        conn.commit()
        conn.close()

        stats = backfill(db_path, dry_run=False, days=30, logger=None)
        assert stats["scanned"] == 3
        assert stats["updated"] == 1
        assert stats["skipped_already_has"] == 1
        assert stats["skipped_no_cache"] == 1
        assert stats["errors"] == 0
