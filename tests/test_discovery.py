from __future__ import annotations

import json
import os
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from movietrace.db.schema import initialize_database
from movietrace.pipeline.discovery import (
    _build_source_summary,
    _build_reason_text,
    _compute_discovery_stats,
    _ensure_fp_data,
    _lookup_canonical_id,
    run_discovery,
)
from movietrace.pipeline.multi_source_merge import MergedCandidate


@pytest.fixture
def db_conn():
    conn = sqlite3.connect(":memory:")
    conn.execute("pragma foreign_keys = on")
    return conn


# ── _build_source_summary tests ─────────────────────────────────────────


class TestBuildSourceSummary:
    def test_includes_all_sources(self):
        c_dict = {
            "tmdb_id": 76479, "title": "The Boys", "media_type": "tv",
            "fp_items": [{"platform": "netflix", "ranking": 1, "days_total": 32}],
            "tmdb_data": {"popularity": 569.2, "vote_average": 8.45, "vote_count": 12247},
            "trakt_data": {"watchers": 5520, "rating": 8.38, "votes": 36983},
            "imdb_rating": 8.6, "imdb_votes": 853757,
        }
        summary = _build_source_summary(c_dict)
        assert "fp" in summary
        assert "tmdb" in summary
        assert "trakt" in summary
        assert "imdb" in summary

    def test_fp_only(self):
        c_dict = {
            "fp_items": [{"platform": "netflix", "ranking": 3, "days_total": 10}],
        }
        summary = _build_source_summary(c_dict)
        assert "fp" in summary
        assert "tmdb" not in summary

    def test_no_data_returns_empty_sections(self):
        c_dict = {}
        summary = _build_source_summary(c_dict)
        assert summary == {}


# ── _build_reason_text tests ────────────────────────────────────────────


class TestBuildReasonText:
    def test_includes_fp_info(self):
        c = MergedCandidate(tmdb_id=100, imdb_id=None, title="Test", media_type="movie")
        c.fp_items = [{"platform": "netflix", "ranking": 1, "days_total": 32}]
        text = _build_reason_text(c, {})
        assert "Netflix" in text
        assert "#1" in text

    def test_includes_tmdb_popularity(self):
        c = MergedCandidate(tmdb_id=100, imdb_id=None, title="Test", media_type="movie")
        c.tmdb_data = {"popularity": 500.0, "vote_average": 8.0, "vote_count": 10000}
        text = _build_reason_text(c, {})
        assert "TMDb popularity" in text

    def test_includes_trakt_watchers(self):
        c = MergedCandidate(tmdb_id=100, imdb_id=None, title="Test", media_type="movie")
        c.trakt_data = {"watchers": 5000, "rating": 8.5, "votes": 10000}
        text = _build_reason_text(c, {})
        assert "实时观看" in text

    def test_fallback_when_no_data(self):
        c = MergedCandidate(tmdb_id=100, imdb_id=None, title="Test", media_type="movie")
        text = _build_reason_text(c, {})
        assert "多源评分数据待补充" in text


# ── _lookup_canonical_id tests ──────────────────────────────────────────


class TestLookupCanonicalId:
    def test_finds_canonical_id(self, db_conn):
        db_conn.execute(
            "create table if not exists canonical_items (id integer primary key, canonical_item_key text, title text, content_type text, content_granularity text)"
        )
        db_conn.execute(
            "create table if not exists external_ids (id integer primary key, canonical_item_id integer references canonical_items(id), source text, external_id text)"
        )
        db_conn.execute(
            "insert into canonical_items (id, canonical_item_key, title, content_type, content_granularity) values (1, 'k1', 'T', 'movie', 'movie')"
        )
        db_conn.execute(
            "insert into external_ids (canonical_item_id, source, external_id) values (1, 'tmdb', '76479')"
        )
        db_conn.commit()
        assert _lookup_canonical_id(db_conn, 76479) == 1

    def test_returns_none_when_not_found(self, db_conn):
        db_conn.execute(
            "create table if not exists external_ids (id integer primary key, canonical_item_id integer references canonical_items(id), source text, external_id text)"
        )
        db_conn.commit()
        assert _lookup_canonical_id(db_conn, 99999) is None


# ── run_discovery integration tests ────────────────────────────────────


class TestRunDiscovery:
    def test_ensure_fp_data_ignores_future_dates_when_checking_target_date(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            initialize_database(db_path)
            conn = sqlite3.connect(db_path)
            conn.execute(
                """insert into flixpatrol_top10
                   (fp_id, title, content_type, platform, country,
                    snapshot_date, ranking, raw_payload_json)
                   values (?, ?, ?, ?, ?, ?, ?, ?)""",
                ("future1", "Future Title", "movie", "netflix", "united-states",
                 "2026-05-14", 1, "{}"),
            )
            conn.commit()

            class FakeClient:
                def __init__(self, api_key, timeout=60, *, db_path="", request_date=""):
                    self.api_key = api_key

                def fetch_all_platforms(self, date_from=None, **kwargs):
                    return {
                        "results": {
                            "united-states/netflix/movie": [
                                {
                                    "fp_id": "target1",
                                    "title": "Target Title",
                                    "content_type": "movie",
                                    "platform": "netflix",
                                    "country": "united-states",
                                    "snapshot_date": "2026-05-13",
                                    "ranking": 1,
                                    "ranking_last": 2,
                                    "value": 10,
                                    "days_total": 3,
                                    "tmdb_id": 123,
                                    "imdb_id": 456,
                                }
                            ]
                        },
                        "planned_calls": 1,
                        "actual_calls": 1,
                        "tv_calls": 0,
                        "movie_calls": 1,
                    }

            with patch("movietrace.sources.flixpatrol_api.load_api_key", return_value="key"):
                with patch("movietrace.sources.flixpatrol_api.FlixPatrolClient", FakeClient):
                    _ensure_fp_data(conn, "2026-05-13", db_path=db_path)

            count = conn.execute(
                "select count(*) from flixpatrol_top10 where snapshot_date = ?",
                ("2026-05-13",),
            ).fetchone()[0]
            assert count == 1
            conn.close()
        finally:
            os.unlink(db_path)

    def test_empty_fp_data_returns_gracefully(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            initialize_database(db_path)
            result = run_discovery(date_from="2026-05-13", dry_run=True, db_path=db_path)
            stats = result.get("stats", {})
            # May get "no_data" if merge produces nothing
            assert isinstance(stats, dict)
        finally:
            os.unlink(db_path)


# ── Stats tests ─────────────────────────────────────────────────────────


class TestComputeDiscoveryStats:
    def test_counts_priorities(self):
        scored = [
            {"hot_score": 90, "priority": "P0"},
            {"hot_score": 80, "priority": "P1"},
            {"hot_score": 80, "priority": "P1"},
            {"hot_score": 60, "priority": "P2"},
            {"hot_score": 40, "priority": "P3"},
            {"hot_score": 30, "priority": "P3"},
        ]
        passed = [s for s in scored if s["hot_score"] >= 50]
        stats = _compute_discovery_stats(scored, passed, {})
        assert stats["total_merged"] == 6
        assert stats["total_passed"] == 4
        assert stats["P0"] == 1
        assert stats["P1"] == 2
        assert stats["P2"] == 1


# ── Auto-register canonical_item tests (P1.9) ───────────────────────────


class TestEnsureCanonicalItem:
    def test_registers_movie_candidate(self):
        from movietrace.pipeline.discovery import _ensure_canonical_item, _lookup_canonical_id
        from movietrace.db.schema import initialize_database

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            initialize_database(db_path)
            conn = sqlite3.connect(db_path)
            candidate = {
                "tmdb_id": 99999, "title": "Test Movie",
                "media_type": "movie", "year": 2026,
            }
            cid = _ensure_canonical_item(conn, candidate)
            assert cid is not None
            # Verify canonical_item
            row = conn.execute(
                "select canonical_item_key, title, content_type, content_granularity from canonical_items where id=?",
                (cid,),
            ).fetchone()
            assert row[0] == "tmdb:movie:99999"
            assert row[1] == "Test Movie"
            assert row[2] == "movie"
            assert row[3] == "movie"
            # Verify external_ids
            found = _lookup_canonical_id(conn, 99999)
            assert found == cid
            conn.close()
        finally:
            os.unlink(db_path)

    def test_registers_tv_candidate(self):
        from movietrace.pipeline.discovery import _ensure_canonical_item
        from movietrace.db.schema import initialize_database

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            initialize_database(db_path)
            conn = sqlite3.connect(db_path)
            candidate = {
                "tmdb_id": 88888, "title": "Test Show",
                "media_type": "tv", "year": 2025,
            }
            cid = _ensure_canonical_item(conn, candidate)
            row = conn.execute(
                "select canonical_item_key, content_type, content_granularity, season_number from canonical_items where id=?",
                (cid,),
            ).fetchone()
            assert row[0] == "tmdb:tv:88888:season:1"
            assert row[1] == "tv"
            assert row[2] == "season"
            assert row[3] == 1
            conn.close()
        finally:
            os.unlink(db_path)

    def test_idempotent(self):
        from movietrace.pipeline.discovery import _ensure_canonical_item
        from movietrace.db.schema import initialize_database

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            initialize_database(db_path)
            conn = sqlite3.connect(db_path)
            candidate = {"tmdb_id": 77777, "title": "Idempotent Test", "media_type": "movie"}
            cid1 = _ensure_canonical_item(conn, candidate)
            cid2 = _ensure_canonical_item(conn, candidate)
            assert cid1 == cid2
            # Only one row
            count = conn.execute(
                "select count(*) from canonical_items where canonical_item_key='tmdb:movie:77777'"
            ).fetchone()[0]
            assert count == 1
            # Only one external_ids row
            ext_count = conn.execute(
                "select count(*) from external_ids where source='tmdb' and external_id='movie:77777'"
            ).fetchone()[0]
            assert ext_count == 1
            conn.close()
        finally:
            os.unlink(db_path)

    def test_returns_none_when_no_tmdb_id(self):
        from movietrace.pipeline.discovery import _ensure_canonical_item
        from movietrace.db.schema import initialize_database

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            initialize_database(db_path)
            conn = sqlite3.connect(db_path)
            cid = _ensure_canonical_item(conn, {"title": "No ID", "media_type": "movie"})
            assert cid is None
            conn.close()
        finally:
            os.unlink(db_path)


# ── P1.10-D Fallback tests ────────────────────────────────────────────────


class TestSourceFallback:
    def test_find_fallback_snapshot_returns_previous_date(self):
        from movietrace.pipeline.discovery import _find_fallback_snapshot
        from movietrace.db.schema import initialize_database

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            initialize_database(db_path)
            conn = sqlite3.connect(db_path)
            conn.execute(
                "insert into tmdb_trending (tmdb_id, media_type, title, popularity, source_endpoint, source_page, snapshot_date, raw_payload_json) values (?, ?, ?, ?, ?, ?, ?, ?)",
                (100, "movie", "Test", 100.0, "trending/day", 1, "2026-05-13", "{}"),
            )
            conn.commit()
            result = _find_fallback_snapshot(conn, "tmdb", "2026-05-14", 30)
            assert result == "2026-05-13"
            conn.close()
        finally:
            os.unlink(db_path)

    def test_find_fallback_snapshot_respects_max_staleness(self):
        from movietrace.pipeline.discovery import _find_fallback_snapshot
        from movietrace.db.schema import initialize_database

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            initialize_database(db_path)
            conn = sqlite3.connect(db_path)
            conn.execute(
                "insert into tmdb_trending (tmdb_id, media_type, title, popularity, source_endpoint, source_page, snapshot_date, raw_payload_json) values (?, ?, ?, ?, ?, ?, ?, ?)",
                (100, "movie", "Test", 100.0, "trending/day", 1, "2026-04-01", "{}"),
            )
            conn.commit()
            result = _find_fallback_snapshot(conn, "tmdb", "2026-05-14", 30)
            assert result is None
            conn.close()
        finally:
            os.unlink(db_path)

    def test_resolve_source_dates_fresh_all(self):
        from movietrace.pipeline.discovery import _resolve_source_dates_with_fallback
        from movietrace.db.schema import initialize_database

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            initialize_database(db_path)
            conn = sqlite3.connect(db_path)
            dates = _resolve_source_dates_with_fallback(
                conn, "2026-05-14",
                flixpatrol_rows=120, tmdb_rows=60, trakt_rows=40,
            )
            assert dates["flixpatrol"] == "2026-05-14"
            assert dates["tmdb"] == "2026-05-14"
            assert dates["trakt"] == "2026-05-14"
            conn.close()
        finally:
            os.unlink(db_path)

    def test_resolve_source_dates_fallback_on_error(self):
        from movietrace.pipeline.discovery import _resolve_source_dates_with_fallback
        from movietrace.db.schema import initialize_database

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            initialize_database(db_path)
            conn = sqlite3.connect(db_path)
            # Seed previous TMDb data for fallback
            conn.execute(
                "insert into tmdb_trending (tmdb_id, media_type, title, popularity, source_endpoint, source_page, snapshot_date, raw_payload_json) values (?, ?, ?, ?, ?, ?, ?, ?)",
                (100, "movie", "Old", 100.0, "trending/day", 1, "2026-05-13", "{}"),
            )
            conn.commit()
            dates = _resolve_source_dates_with_fallback(
                conn, "2026-05-14",
                flixpatrol_rows=120,
                tmdb_rows=0, tmdb_error="API timeout",
                trakt_rows=40,
                fallback_cfg={"enabled": True, "max_staleness_days": 30, "sources": {"flixpatrol": True, "tmdb": True, "trakt": True}},
            )
            assert dates["flixpatrol"] == "2026-05-14"
            assert dates["tmdb"] == "2026-05-13"  # fallback
            assert dates["trakt"] == "2026-05-14"
            conn.close()
        finally:
            os.unlink(db_path)

    def test_resolve_source_dates_failed_no_fallback(self):
        from movietrace.pipeline.discovery import _resolve_source_dates_with_fallback
        from movietrace.db.schema import initialize_database

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            initialize_database(db_path)
            conn = sqlite3.connect(db_path)
            dates = _resolve_source_dates_with_fallback(
                conn, "2026-05-14",
                flixpatrol_rows=120,
                tmdb_rows=0, tmdb_error="API unreachable",
                trakt_rows=40,
                fallback_cfg={"enabled": True, "max_staleness_days": 30, "sources": {"tmdb": True}},
            )
            assert dates["flixpatrol"] == "2026-05-14"
            assert dates["tmdb"] is None  # failed, no prior data
            assert dates["trakt"] == "2026-05-14"
            conn.close()
        finally:
            os.unlink(db_path)
