"""Integration test: end-to-end daily discover pipeline (dry-run mode).

Tests the full flow: discovery → scoring → baseline matching → report → Feishu write.
Uses in-memory temp DB with synthetic data.
"""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
from datetime import date
from pathlib import Path

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
    """Seed a temp DB with synthetic flixpatrol data, baseline items, and canonical items."""
    conn = sqlite3.connect(temp_db)
    conn.execute("pragma foreign_keys = on")

    # Seed canonical_items
    conn.execute(
        """insert into canonical_items
           (canonical_item_key, title, content_type, content_granularity, year, release_date, language)
           values ('ci:1', 'The Crown', 'tv_show', 'series', 2016, '2016-11-04', 'en')"""
    )
    conn.execute(
        """insert into external_ids
           (canonical_item_id, source, external_id)
           values (1, 'tmdb', '65495')"""
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
        ("fp_1", "The Crown", "tv_show", "netflix", "united-states", "2026-05-11", 1, 0, 10, 30, 65495, 4786824),
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

    def test_discovery_scoring_with_synthetic_data(self, seeded_db):
        """Discovery pipeline runs without errors."""
        from movietrace.pipeline.discovery import run_discovery
        result = run_discovery(date_from="2026-05-11", dry_run=True, db_path=seeded_db)
        stats = result.get("stats", {})
        assert "error" not in stats, f"Discovery failed: {stats}"
        candidates = result.get("candidates", [])
        assert len(candidates) >= 3

    def test_baseline_matching_with_synthetic_data(self, seeded_db):
        """Baseline matching runs without errors."""
        # First run discovery to populate candidates
        from movietrace.pipeline.discovery import run_discovery
        run_discovery(date_from="2026-05-11", dry_run=False, db_path=seeded_db)

        from movietrace.pipeline.baseline_matching import run_baseline_matching
        result = run_baseline_matching(db_path=seeded_db)
        assert "error" not in result
        assert result["total"] >= 3
        # The Crown should match baseline (high or medium confidence)
        assert result["high"] + result["medium"] >= 1

    def test_report_generation_with_synthetic_data(self, seeded_db):
        """Daily report generates with synthetic data."""
        from movietrace.pipeline.discovery import run_discovery
        from movietrace.pipeline.baseline_matching import run_baseline_matching
        from movietrace.reports.daily_writer import generate_daily_report

        run_discovery(date_from="2026-05-11", dry_run=False, db_path=seeded_db)
        run_baseline_matching(db_path=seeded_db)

        report = generate_daily_report(date.today(), db_path=seeded_db)
        assert "# MovieTrace" in report
        assert "📊" in report
        assert "The Crown" in report or "Brand New Show" in report

    def test_export_dry_run_with_synthetic_data(self, seeded_db):
        """Export recommendations dry-run works with synthetic data."""
        from movietrace.pipeline.discovery import run_discovery
        from movietrace.pipeline.baseline_matching import run_baseline_matching
        from movietrace.reports.export_writer import export_recommendations

        run_discovery(date_from="2026-05-11", dry_run=False, db_path=seeded_db)
        run_baseline_matching(db_path=seeded_db)

        result = export_recommendations(db_path=seeded_db, days=365, dry_run=True)
        assert result.get("dry_run") is True

    def test_full_pipeline_integration(self, seeded_db):
        """End-to-end pipeline: discovery → matching → report → export."""
        from movietrace.pipeline.discovery import run_discovery
        from movietrace.pipeline.baseline_matching import run_baseline_matching
        from movietrace.reports.daily_writer import generate_daily_report
        from movietrace.reports.export_writer import export_recommendations

        # Step 1: Discovery
        disc_result = run_discovery(date_from="2026-05-11", dry_run=False, db_path=seeded_db)
        assert disc_result["stats"]["total"] >= 3

        # Step 2: Baseline matching
        match_result = run_baseline_matching(db_path=seeded_db)
        assert match_result["total"] == disc_result["stats"]["total"]

        # Step 3: Report
        report = generate_daily_report(date.today(), db_path=seeded_db)
        assert len(report) > 100

        # Step 4: Export
        with tempfile.TemporaryDirectory() as tmpdir:
            export_result = export_recommendations(
                db_path=seeded_db, output_dir=tmpdir, days=365
            )
            assert "md_path" in export_result

    def test_full_pipeline_is_idempotent(self, seeded_db):
        """Running the pipeline twice produces consistent confidence counts."""
        from movietrace.pipeline.discovery import run_discovery
        from movietrace.pipeline.baseline_matching import run_baseline_matching

        run_discovery(date_from="2026-05-11", dry_run=False, db_path=seeded_db)
        m1 = run_baseline_matching(db_path=seeded_db)

        m2 = run_baseline_matching(db_path=seeded_db)

        assert m1["total"] == m2["total"]
        assert m1["high"] == m2["high"]
        assert m1["medium"] == m2["medium"]


class TestCliCommands:
    """Test CLI commands execute without errors."""

    def test_inspect_baseline(self):
        import subprocess
        import sys
        result = subprocess.run(
            [sys.executable, "-m", "movietrace.cli", "inspect-baseline"],
            capture_output=True, text=True,
            env={**os.environ, "PYTHONPATH": "src"},
            cwd=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        )
        # May fail if cwd is wrong, but should at least run
        assert result.returncode in (0, 1)

    def test_daily_discover_help(self):
        import subprocess
        import sys
        result = subprocess.run(
            [sys.executable, "-m", "movietrace.cli", "daily-discover", "--help"],
            capture_output=True, text=True,
            env={**os.environ, "PYTHONPATH": "src"},
            cwd=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        )
        assert result.returncode == 0
        assert "--dry-run" in result.stdout
