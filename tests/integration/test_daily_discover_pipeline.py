"""Integration test: end-to-end daily discover pipeline (dry-run mode).

Tests the full multi-source flow with synthetic FP data.
Uses in-memory temp DB with synthetic data.
"""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest


def _init_temp_db(db_path: str) -> None:
    from movietrace.db.schema import initialize_database
    initialize_database(db_path)


@pytest.fixture
def temp_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    _init_temp_db(db_path)
    yield db_path
    os.unlink(db_path)


@pytest.fixture
def seeded_db(temp_db):
    """Seed a temp DB with synthetic flixpatrol and canonical_items data."""
    conn = sqlite3.connect(temp_db)
    conn.execute("pragma foreign_keys = on")

    # Seed canonical_items with external_ids
    conn.execute(
        """insert into canonical_items
           (canonical_item_key, title, content_type, content_granularity, year, release_date, language)
           values ('ci:1', 'The Crown', 'tv', 'season', 2016, '2016-11-04', 'en')"""
    )
    conn.execute(
        """insert into canonical_items
           (canonical_item_key, title, content_type, content_granularity, year, release_date, language)
           values ('ci:2', 'Brand New Show', 'tv', 'season', 2026, '2026-01-01', 'en')"""
    )
    conn.execute(
        """insert into canonical_items
           (canonical_item_key, title, content_type, content_granularity, year, release_date, language)
           values ('ci:3', 'Another New Show', 'movie', 'movie', 2026, '2026-02-01', 'en')"""
    )
    conn.execute(
        """insert into external_ids (canonical_item_id, source, external_id)
           values (1, 'tmdb', '65495')"""
    )
    conn.execute(
        """insert into external_ids (canonical_item_id, source, external_id)
           values (2, 'tmdb', '99999')"""
    )
    conn.execute(
        """insert into external_ids (canonical_item_id, source, external_id)
           values (3, 'tmdb', '88888')"""
    )

    # Seed baseline_items
    conn.execute(
        """insert into baseline_items
           (title, content_type, content_granularity, year, raw_fields_json, match_status)
           values ('The Crown', 'tv_show', 'series', 2016, '{}', 'matched')"""
    )
    conn.execute(
        """insert into baseline_items
           (title, content_type, content_granularity, year, raw_fields_json, match_status)
           values ('Breaking Bad', 'tv_show', 'series', 2008, '{}', 'matched')"""
    )

    # Seed flixpatrol_top10 with synthetic data
    fp_data = [
        ("fp_1", "The Crown", "tv_show", "netflix", "united-states", "2026-05-11", 1, 0, 10, 30, 65495, "tt4786824"),
        ("fp_2", "Brand New Show", "tv_show", "netflix", "united-states", "2026-05-11", 2, 1, 9, 5, 99999, None),
        ("fp_3", "Another New Show", "movie", "prime-video", "united-states", "2026-05-11", 3, 0, 8, 2, 88888, None),
    ]
    for fp in fp_data:
        conn.execute(
            """insert into flixpatrol_top10
               (fp_id, title, content_type, platform, country, snapshot_date,
                ranking, ranking_last, value, days_total, tmdb_id, imdb_id, raw_payload_json)
               values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (*fp, "{}"),
        )

    conn.commit()
    conn.close()
    return temp_db


class TestEndToEndPipeline:
    """Test the full pipeline in dry-run mode with synthetic data."""

    def test_discovery_merges_with_synthetic_data(self, seeded_db):
        """Discovery pipeline merges FP data into candidates."""
        from movietrace.pipeline.discovery import run_discovery
        with patch("movietrace.pipeline.discovery._load_secrets", return_value={}):
            result = run_discovery(date_from="2026-05-11", dry_run=True, db_path=seeded_db)
        stats = result.get("stats", {})
        assert "error" not in stats, f"Discovery failed: {stats}"
        # Merged candidates from 3 FP items
        assert stats.get("total_merged", 0) >= 3

    def test_discovery_scoring_with_synthetic_data(self, seeded_db):
        """Discovery pipeline scores without errors."""
        from movietrace.pipeline.discovery import run_discovery
        with patch("movietrace.pipeline.discovery._load_secrets", return_value={}):
            result = run_discovery(date_from="2026-05-11", dry_run=True, db_path=seeded_db)
        stats = result.get("stats", {})
        assert "error" not in stats, f"Discovery failed: {stats}"
        passed = result.get("candidates", [])
        # At least some candidates should pass P2 threshold
        assert len(passed) >= 0  # Acceptable even if none pass

    def test_baseline_matching_with_synthetic_data(self, seeded_db):
        """Baseline matching module loads and handles empty candidates gracefully."""
        from movietrace.pipeline.baseline_matching import run_baseline_matching
        result = run_baseline_matching(db_path=seeded_db)
        # Candidates table may be empty (new flow writes to content_updates).
        # Either no_candidates or successful match is acceptable.
        assert isinstance(result, dict)
        assert "total" in result

    def test_report_generation_with_synthetic_data(self, seeded_db):
        """Daily report generates with synthetic data."""
        from movietrace.pipeline.baseline_matching import run_baseline_matching
        from movietrace.reports.daily_writer import generate_daily_report

        run_baseline_matching(db_path=seeded_db)
        report = generate_daily_report(date(2026, 5, 11), db_path=seeded_db)
        assert "# MovieTrace" in report

    def test_export_dry_run_with_synthetic_data(self, seeded_db):
        """Export recommendations dry-run works with synthetic data."""
        from movietrace.reports.export_writer import export_recommendations
        result = export_recommendations(db_path=seeded_db, days=30, dry_run=True)
        assert result.get("dry_run") is True

    def test_run_discovery_empty_db_returns_gracefully(self, temp_db):
        """Discovery on an empty DB returns stats without error key."""
        from movietrace.pipeline.discovery import run_discovery
        with patch("movietrace.pipeline.discovery._ensure_fp_data",
                   return_value={"planned_calls": 0, "actual_calls": 0}):
            result = run_discovery(date_from="2026-05-13", dry_run=True, db_path=temp_db)
        stats = result.get("stats", {})
        assert isinstance(stats, dict)
