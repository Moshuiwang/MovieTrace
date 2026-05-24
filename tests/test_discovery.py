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
    _should_skip_enrichment,
    _write_content_updates,
    _write_current_discovery_batch,
    run_discovery,
    should_write_observation,
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
        # P1.24: 扩展了 summary 的字段，包含 imdb_id, last_episode_to_air, genres, score_breakdown, row_duration_hours
        assert summary.get("imdb_id") is None
        assert summary.get("last_episode_to_air") is None
        assert summary.get("genres") == []
        assert summary.get("score_breakdown") == {}
        assert summary.get("row_duration_hours") == 0.0
        # ops_note 和 is_soap 仅在有数据时才存在
        assert "ops_note" not in summary
        assert "is_soap" not in summary


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
            "insert into external_ids (canonical_item_id, source, external_id) values (1, 'tmdb', 'movie:76479')"
        )
        db_conn.commit()
        assert _lookup_canonical_id(db_conn, 76479) == 1

    def test_returns_none_when_not_found(self, db_conn):
        db_conn.execute(
            "create table if not exists external_ids (id integer primary key, canonical_item_id integer references canonical_items(id), source text, external_id text)"
        )
        db_conn.commit()
        assert _lookup_canonical_id(db_conn, 99999) is None

    def test_tv_movie_collision_isolated(self, db_conn):
        """movie:100 and tv:100 are different namespace entries."""
        db_conn.execute(
            "create table if not exists canonical_items (id integer primary key, canonical_item_key text, title text, content_type text, content_granularity text)"
        )
        db_conn.execute(
            "create table if not exists external_ids (id integer primary key, canonical_item_id integer references canonical_items(id), source text, external_id text)"
        )
        db_conn.execute(
            "insert into canonical_items (id, canonical_item_key, title, content_type, content_granularity) values (1, 'k1', 'Movie 100', 'movie', 'movie')"
        )
        db_conn.execute(
            "insert into external_ids (canonical_item_id, source, external_id) values (1, 'tmdb', 'movie:100')"
        )
        db_conn.commit()
        # TV lookup for same numeric id must NOT return the movie
        assert _lookup_canonical_id(db_conn, 100, media_type="tv") is None
        # Movie lookup returns correct match
        assert _lookup_canonical_id(db_conn, 100, media_type="movie") == 1

    def test_tv_lookup_finds_tv_prefix(self, db_conn):
        db_conn.execute(
            "create table if not exists canonical_items (id integer primary key, canonical_item_key text, title text, content_type text, content_granularity text)"
        )
        db_conn.execute(
            "create table if not exists external_ids (id integer primary key, canonical_item_id integer references canonical_items(id), source text, external_id text)"
        )
        db_conn.execute(
            "insert into canonical_items (id, canonical_item_key, title, content_type, content_granularity) values (2, 'k2', 'Show 200', 'tv', 'season')"
        )
        db_conn.execute(
            "insert into external_ids (canonical_item_id, source, external_id) values (2, 'tmdb', 'tv:200')"
        )
        db_conn.commit()
        assert _lookup_canonical_id(db_conn, 200, media_type="tv") == 2
        assert _lookup_canonical_id(db_conn, 200, media_type="show") == 2


# ── _write_content_updates tests ────────────────────────────────────────


class TestWriteContentUpdates:
    def test_discovery_content_update_id_includes_media_namespace(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            initialize_database(db_path)
            conn = sqlite3.connect(db_path)
            conn.execute(
                """insert into canonical_items
                   (id, canonical_item_key, title, content_type, content_granularity)
                   values (1, 'tmdb:movie:100', 'Movie 100', 'movie', 'movie')"""
            )
            conn.execute(
                """insert into canonical_items
                   (id, canonical_item_key, title, content_type, content_granularity)
                   values (2, 'tmdb:tv:100:season:1', 'Show 100', 'tv', 'season')"""
            )
            conn.execute(
                """insert into external_ids (canonical_item_id, source, external_id)
                   values (1, 'tmdb', 'movie:100')"""
            )
            conn.execute(
                """insert into external_ids (canonical_item_id, source, external_id)
                   values (2, 'tmdb', 'tv:100')"""
            )
            conn.commit()

            written = _write_content_updates(
                conn,
                [
                    {"tmdb_id": 100, "title": "Movie 100", "media_type": "movie"},
                    {"tmdb_id": 100, "title": "Show 100", "media_type": "tv"},
                ],
                "2026-05-14",
            )

            assert written == 2
            rows = conn.execute(
                "select content_update_id, canonical_item_id from content_updates order by canonical_item_id"
            ).fetchall()
            assert rows == [
                ("discovery:movie:100:2026-05-14", 1),
                ("discovery:tv:100:2026-05-14", 2),
            ]
            conn.close()
        finally:
            os.unlink(db_path)

    def test_discovery_content_update_id_remains_idempotent_per_media_namespace(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            initialize_database(db_path)
            conn = sqlite3.connect(db_path)
            conn.execute(
                """insert into canonical_items
                   (id, canonical_item_key, title, content_type, content_granularity)
                   values (1, 'tmdb:movie:100', 'Movie 100', 'movie', 'movie')"""
            )
            conn.execute(
                """insert into external_ids (canonical_item_id, source, external_id)
                   values (1, 'tmdb', 'movie:100')"""
            )
            conn.commit()

            candidate = {"tmdb_id": 100, "title": "Movie 100", "media_type": "movie"}
            assert _write_content_updates(conn, [candidate], "2026-05-14") == 1
            assert _write_content_updates(conn, [candidate], "2026-05-14") == 0
            assert _write_content_updates(conn, [candidate], "2026-05-15") == 1

            rows = conn.execute(
                "select content_update_id from content_updates order by content_update_id"
            ).fetchall()
            assert rows == [
                ("discovery:movie:100:2026-05-14",),
                ("discovery:movie:100:2026-05-15",),
            ]
            conn.close()
        finally:
            os.unlink(db_path)


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
            with patch("movietrace.pipeline.discovery._ensure_fp_data",
                       return_value={"planned_calls": 0, "actual_calls": 0}):
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

    def test_enrichment_detail_fields_present(self):
        """P1.37: _compute_discovery_stats must include enrich_imdb_backfill/omdb/tmdb_detail."""
        scored = [{"hot_score": 80, "priority": "P1"}]
        passed = scored[:]
        enrich_stats = {
            "imdb_backfill": {"backfilled": 5, "total": 10, "errors": []},
            "omdb": {"enriched": 8, "api_calls": 3, "cache_hits": 5, "errors": 0},
            "tmdb_detail": {"enriched": 7, "api_calls": 2, "cache_hits": 5, "errors": 0},
        }
        stats = _compute_discovery_stats(scored, passed, enrich_stats)
        assert "enrich_imdb_backfill" in stats
        assert "enrich_omdb" in stats
        assert "enrich_tmdb_detail" in stats
        assert stats["enrich_imdb_backfill"]["backfilled"] == 5
        assert stats["enrich_omdb"]["enriched"] == 8
        assert stats["enrich_tmdb_detail"]["enriched"] == 7

    def test_enrichment_detail_empty_when_not_run(self):
        """P1.37: enrich fields default to empty dict when enrichment not run."""
        scored = [{"hot_score": 60, "priority": "P2"}]
        passed = scored[:]
        stats = _compute_discovery_stats(scored, passed, {})
        assert stats["enrich_imdb_backfill"] == {}
        assert stats["enrich_omdb"] == {}
        assert stats["enrich_tmdb_detail"] == {}

    def test_fp_stats_fields_present(self):
        """P1.37: fp_error and fp_inserted should be included in stats."""
        scored = []
        passed = []
        fp_stats = {"planned_calls": 2, "actual_calls": 2, "inserted": 120, "error": None}
        stats = _compute_discovery_stats(scored, passed, {}, fp_stats)
        assert stats["fp_planned"] == 2
        assert stats["fp_actual"] == 2
        assert stats["fp_inserted"] == 120
        assert stats["fp_error"] is None


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


# ── P1.12-B: Dry-run no business writes tests ────────────────────────────


class TestDryRunNoBusinessWrites:
    """dry_run=True must not write to canonical_items / external_ids / content_updates."""

    def test_dry_run_does_not_write_canonical_items(self):
        from movietrace.db.schema import initialize_database

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            initialize_database(db_path)
            with patch("movietrace.pipeline.discovery._ensure_fp_data",
                       return_value={"planned_calls": 0, "actual_calls": 0}):
                result = run_discovery(date_from="2026-05-13", dry_run=True, db_path=db_path)

            conn = sqlite3.connect(db_path)
            ci_count = conn.execute("select count(*) from canonical_items").fetchone()[0]
            ext_count = conn.execute("select count(*) from external_ids").fetchone()[0]
            cu_count = conn.execute("select count(*) from content_updates").fetchone()[0]
            conn.close()

            assert ci_count == 0, f"dry_run should not write canonical_items, found {ci_count}"
            assert ext_count == 0, f"dry_run should not write external_ids, found {ext_count}"
            assert cu_count == 0, f"dry_run should not write content_updates, found {cu_count}"
        finally:
            os.unlink(db_path)

    def test_dry_run_reports_would_be_registered(self):
        """dry_run=True returns would_be_registered stat, not auto_registered."""
        from movietrace.db.schema import initialize_database

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            initialize_database(db_path)
            with patch("movietrace.pipeline.discovery._ensure_fp_data",
                       return_value={"planned_calls": 0, "actual_calls": 0}):
                result = run_discovery(date_from="2026-05-13", dry_run=True, db_path=db_path)

            stats = result.get("stats", {})
            # auto_registered must be 0 (no writes happened)
            assert stats.get("auto_registered", 0) == 0
            assert isinstance(stats, dict)
        finally:
            os.unlink(db_path)


# ── P1.24-B: Row duration tests ────────────────────────────────────────────


class TestComputeRowDuration:
    def test_movie_returns_2(self):
        from movietrace.pipeline.discovery import compute_row_duration_hours
        c_dict = {"media_type": "movie"}
        result = compute_row_duration_hours(c_dict, None, None)
        assert result == 2.0

    def test_tv_no_tmdb_id_returns_0(self):
        from movietrace.pipeline.discovery import compute_row_duration_hours
        c_dict = {"media_type": "tv"}
        result = compute_row_duration_hours(c_dict, None, None)
        assert result == 0.0

    def test_tv_no_last_aired_season_returns_0(self):
        from movietrace.pipeline.discovery import compute_row_duration_hours
        c_dict = {
            "media_type": "tv",
            "tmdb_id": 1,
            "tmdb_data": {"last_episode_to_air": None},
        }
        result = compute_row_duration_hours(c_dict, None, None)
        assert result == 0.0

    def test_tv_a_lib_empty_sums_aired_episode_counts(self):
        """a_lib_max=0 → 累加 S1..last_aired_season 的已播集数。
        对最新季用 last_episode_to_air.episode_number(已播,排除未播)。"""
        from movietrace.pipeline.discovery import compute_row_duration_hours
        from unittest.mock import MagicMock

        c_dict = {
            "media_type": "tv",
            "tmdb_id": 1,
            "tmdb_data": {
                # last_aired = S3E5;S3 整季计划 10 集,但只播了 5 集
                "last_episode_to_air": {"season_number": 3, "episode_number": 5},
                "number_of_episodes": 100,  # 用不到了(含未播,故意写偏)
            },
        }
        conn = MagicMock()
        tmdb_client = MagicMock()

        def season_detail_side_effect(c, cli, tv_id, s_n):
            return ({"episode_count": 10}, False)  # 每季都"满"10 集

        with patch("movietrace.pipeline.discovery._query_a_lib_max_season", return_value=0):
            with patch(
                "movietrace.pipeline.discovery.get_tmdb_season_detail_with_cache",
                side_effect=season_detail_side_effect,
            ):
                result = compute_row_duration_hours(c_dict, conn, tmdb_client)
        # 期望:S1(10)+ S2(10)+ S3(5,只播 5 集)= 25
        assert result == 25.0

    def test_tv_a_lib_has_seasons_calculates_delta(self):
        from movietrace.pipeline.discovery import compute_row_duration_hours
        from unittest.mock import MagicMock

        c_dict = {
            "media_type": "tv",
            "tmdb_id": 1,
            "tmdb_data": {
                # last_aired = S6E24(S6 全季已播完)
                "last_episode_to_air": {"season_number": 6, "episode_number": 24},
                "number_of_episodes": 100,
            },
        }
        conn = MagicMock()
        tmdb_client = MagicMock()

        def season_detail_side_effect(c, cli, tv_id, s_n):
            if s_n == 6:
                return ({"episode_count": 24}, False)
            elif s_n == 5:
                return ({"episode_count": 20}, False)
            return (None, False)

        with patch("movietrace.pipeline.discovery._query_a_lib_max_season", return_value=5):
            with patch(
                "movietrace.pipeline.discovery.get_tmdb_season_detail_with_cache",
                side_effect=season_detail_side_effect,
            ):
                # Mock: A 库 S5 有 18 集(缺 2 集)
                with patch("movietrace.pipeline.discovery._query_a_lib_episode_count", return_value=18):
                    result = compute_row_duration_hours(c_dict, conn, tmdb_client)
        # 期望: S6 的 24 集 + S5 缺的 2 集 = 26
        assert result == 26.0

    def test_tv_a_lib_empty_excludes_unaired_in_current_season(self):
        """回归:a_lib_max=0 + 最新季有未播集 → 只算已播,不能用 number_of_episodes。"""
        from movietrace.pipeline.discovery import compute_row_duration_hours
        from unittest.mock import MagicMock

        c_dict = {
            "media_type": "tv",
            "tmdb_id": 1,
            "tmdb_data": {
                # S22 在播,只播到 E5(还有 17 集未播)
                "last_episode_to_air": {"season_number": 22, "episode_number": 5},
                # 假设 S1-S21 各 22 集,S22 计划 22 集 → 462 含未播
                "number_of_episodes": 462,
            },
        }
        conn = MagicMock()
        tmdb_client = MagicMock()

        def season_detail_side_effect(c, cli, tv_id, s_n):
            return ({"episode_count": 22}, False)

        with patch("movietrace.pipeline.discovery._query_a_lib_max_season", return_value=0):
            with patch(
                "movietrace.pipeline.discovery.get_tmdb_season_detail_with_cache",
                side_effect=season_detail_side_effect,
            ):
                result = compute_row_duration_hours(c_dict, conn, tmdb_client)
        # 期望:21 季完整 × 22 集 + S22 已播 5 集 = 467
        assert result == 21 * 22 + 5

    def test_tv_sparse_seasons_only_fetches_listed_seasons(self):
        """回归:长寿节目季号不连续时,不要请求 TMDb 不存在的中间季。"""
        from movietrace.pipeline.discovery import compute_row_duration_hours
        from unittest.mock import MagicMock

        c_dict = {
            "media_type": "tv",
            "tmdb_id": 2035,
            "tmdb_data": {
                "last_episode_to_air": {"season_number": 49, "episode_number": 27},
                "seasons": [
                    {"season_number": 1},
                    {"season_number": 2},
                    {"season_number": 49},
                ],
            },
        }
        conn = MagicMock()
        tmdb_client = MagicMock()
        requested = []

        def season_detail_side_effect(c, cli, tv_id, s_n):
            requested.append(s_n)
            if s_n == 49:
                return ({"episode_count": 30}, False)
            return ({"episode_count": 10}, False)

        with patch("movietrace.pipeline.discovery._query_a_lib_max_season", return_value=0):
            with patch(
                "movietrace.pipeline.discovery.get_tmdb_season_detail_with_cache",
                side_effect=season_detail_side_effect,
            ):
                result = compute_row_duration_hours(c_dict, conn, tmdb_client)

        assert requested == [1, 2, 49]
        assert result == 10 + 10 + 27


# ── P1.24-C: Soap降权tests ────────────────────────────────────────────────


class TestSoapGenreDowngrade:
    def test_soap_genre_forces_p3(self):
        from movietrace.pipeline.discovery import run_discovery
        from movietrace.db.schema import initialize_database

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            initialize_database(db_path)

            def mock_merge(*args, **kwargs):
                from movietrace.pipeline.multi_source_merge import MergedCandidate
                return [
                    MergedCandidate(
                        title="Test Soap",
                        tmdb_id=1,
                        imdb_id="tt0000001",
                        media_type="tv",
                        fp_items=[],
                        tmdb_data={
                            "popularity": 50,
                            "vote_average": 7,
                            "vote_count": 100,
                            "genres": [{"id": 10766, "name": "Soap"}],
                        },
                        trakt_data=None,
                        source_flags={"tmdb"},
                    ),
                ]

            with patch("movietrace.pipeline.discovery._load_secrets", return_value={"omdb": {}, "tmdb": {}}):
                with patch("movietrace.pipeline.discovery._ensure_fp_data",
                           return_value={"planned_calls": 0, "actual_calls": 0}):
                    with patch("movietrace.pipeline.multi_source_merge.merge_three_sources", side_effect=mock_merge):
                        result = run_discovery(date_from="2026-05-13", dry_run=True, db_path=db_path)

            candidates = result.get("candidates", [])
            # P1.57d: pure fallback Soap (has_fresh_signal=False) is suppressed at write gate.
            # The DB has no rows for 2026-05-13, so source_dates will not be fresh → has_fresh_signal=False.
            # Soap still bypasses the hot_score threshold, but should_write_observation returns False.
            assert len(candidates) == 0
            stats = result.get("stats", {})
            assert stats.get("soap_pure_fallback_suppressed", 0) >= 1
        finally:
            os.unlink(db_path)

    def test_non_soap_keeps_original_priority(self):
        from movietrace.pipeline.discovery import run_discovery
        from movietrace.db.schema import initialize_database

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            initialize_database(db_path)

            def mock_merge(*args, **kwargs):
                from movietrace.pipeline.multi_source_merge import MergedCandidate
                return [
                    MergedCandidate(
                        title="Test Drama",
                        tmdb_id=2,
                        imdb_id="tt0000002",
                        media_type="tv",
                        fp_items=[{"ranking": 1, "platform": "netflix", "days_total": 10}],  # 高排名 → 高评分
                        tmdb_data={
                            "popularity": 500,
                            "vote_average": 8,
                            "vote_count": 1000,
                            "genres": [{"id": 18, "name": "Drama"}],
                        },
                        trakt_data={"watchers": 5000, "rating": 8.5, "votes": 1000},
                        source_flags={"tmdb", "trakt", "flixpatrol"},
                    ),
                ]

            # P1.42: Mock source_dates to return fresh dates for all sources
            def mock_resolve_source_dates(*args, **kwargs):
                return {"flixpatrol": "2026-05-13", "tmdb": "2026-05-13", "trakt": "2026-05-13"}

            with patch("movietrace.pipeline.discovery._load_secrets", return_value={"omdb": {}, "tmdb": {}}):
                with patch("movietrace.pipeline.discovery._ensure_fp_data",
                           return_value={"planned_calls": 0, "actual_calls": 0}):
                    with patch("movietrace.pipeline.discovery._resolve_source_dates_with_fallback",
                               side_effect=mock_resolve_source_dates):
                        with patch("movietrace.pipeline.multi_source_merge.merge_three_sources", side_effect=mock_merge):
                            result = run_discovery(date_from="2026-05-13", dry_run=True, db_path=db_path)

            candidates = result.get("candidates", [])
            assert len(candidates) >= 1, f"Expected at least 1 candidate, got {len(candidates)}"
            drama_candidate = candidates[0]
            assert drama_candidate.get("is_soap") == False
            # 不应被降权，应保持原来评分计算的 priority（不是 P3）
            assert drama_candidate.get("priority") in ["P0", "P1", "P2"], f"Got priority {drama_candidate.get('priority')}"
        finally:
            os.unlink(db_path)


class TestComputeDiscoveryStatsFilteredOut:
    def _make_scored(self, content_ids_and_scores: list[tuple[str, float]]) -> list[dict]:
        return [{"content_id": cid, "hot_score": score, "title": cid} for cid, score in content_ids_and_scores]

    def test_filtered_out_sorted_descending_by_hot_score(self):
        from movietrace.pipeline.discovery import _compute_discovery_stats
        all_scored = self._make_scored([
            ("a", 80), ("b", 30), ("c", 60), ("d", 45), ("e", 75),
        ])
        passed = [{"content_id": "a", "priority": "P0"}]
        stats = _compute_discovery_stats(all_scored, passed, {})
        filtered = stats["filtered_out"]
        scores = [item["hot_score"] for item in filtered]
        assert scores == sorted(scores, reverse=True), "filtered_out must be sorted hot_score DESC"

    def test_filtered_out_max_10(self):
        from movietrace.pipeline.discovery import _compute_discovery_stats
        all_scored = self._make_scored([(str(i), float(i)) for i in range(20)])
        passed = []
        stats = _compute_discovery_stats(all_scored, passed, {})
        assert len(stats["filtered_out"]) <= 10

    def test_filtered_out_excludes_passed(self):
        from movietrace.pipeline.discovery import _compute_discovery_stats
        all_scored = self._make_scored([("a", 90), ("b", 40)])
        passed = [{"content_id": "a", "priority": "P0"}]
        stats = _compute_discovery_stats(all_scored, passed, {})
        filtered_ids = [item["content_id"] for item in stats["filtered_out"]]
        assert "a" not in filtered_ids


# ── P1.57d: should_write_observation 矩阵测试 ────────────────────────────────


class TestShouldWriteObservation:
    """Matrix tests for the observation eligibility gate (P1.57d)."""

    def test_pure_fallback_returns_false(self):
        """Pure source-date fallback (has_fresh_signal=False) → not eligible."""
        candidate = {"has_fresh_signal": False, "is_soap": False}
        assert should_write_observation(candidate) is False

    def test_fresh_signal_returns_true(self):
        """Candidate with fresh signal → eligible."""
        candidate = {"has_fresh_signal": True, "is_soap": False}
        assert should_write_observation(candidate) is True

    def test_soap_pure_fallback_returns_false(self):
        """Soap pure fallback (is_soap=True, has_fresh_signal=False) → not eligible.
        P1.57d: Soap threshold exemption does not extend to the write gate."""
        candidate = {"has_fresh_signal": False, "is_soap": True}
        assert should_write_observation(candidate) is False

    def test_soap_with_fresh_signal_returns_true(self):
        """Soap with genuine fresh signal → eligible."""
        candidate = {"has_fresh_signal": True, "is_soap": True}
        assert should_write_observation(candidate) is True

    def test_missing_has_fresh_signal_key_returns_false(self):
        """Candidate dict missing has_fresh_signal key → falsy → not eligible."""
        candidate = {"is_soap": False}
        assert should_write_observation(candidate) is False

    def test_empty_candidate_returns_false(self):
        """Empty candidate dict → not eligible."""
        assert should_write_observation({}) is False


# ── P1.57d: soap_pure_fallback_suppressed 计数集成测试 ───────────────────────


class TestSoapPureFallbackSuppressedCount:
    """Integration tests verifying soap_pure_fallback_suppressed appears in stats."""

    def test_soap_pure_fallback_counted_in_stats(self):
        """When a Soap candidate has no fresh signal, soap_pure_fallback_suppressed >= 1."""
        from movietrace.pipeline.discovery import run_discovery
        from movietrace.db.schema import initialize_database

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            initialize_database(db_path)

            def mock_merge(*args, **kwargs):
                from movietrace.pipeline.multi_source_merge import MergedCandidate
                return [
                    MergedCandidate(
                        title="Soap No Signal",
                        tmdb_id=10,
                        imdb_id="tt0000010",
                        media_type="tv",
                        fp_items=[],
                        tmdb_data={"genres": [{"id": 10766, "name": "Soap"}]},
                        trakt_data=None,
                        source_flags={"tmdb"},
                    ),
                ]

            with patch("movietrace.pipeline.discovery._load_secrets", return_value={"omdb": {}, "tmdb": {}}):
                with patch("movietrace.pipeline.discovery._ensure_fp_data",
                           return_value={"planned_calls": 0, "actual_calls": 0}):
                    with patch("movietrace.pipeline.multi_source_merge.merge_three_sources",
                               side_effect=mock_merge):
                        result = run_discovery(date_from="2026-05-13", dry_run=True, db_path=db_path)

            stats = result.get("stats", {})
            assert "soap_pure_fallback_suppressed" in stats
            assert stats["soap_pure_fallback_suppressed"] >= 1
            assert stats["suppressed_fallback_only"] >= 1
        finally:
            os.unlink(db_path)

    def test_soap_with_fresh_signal_not_counted(self):
        """When a Soap candidate has fresh signal, soap_pure_fallback_suppressed == 0."""
        from movietrace.pipeline.discovery import run_discovery
        from movietrace.db.schema import initialize_database

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            initialize_database(db_path)

            def mock_merge(*args, **kwargs):
                from movietrace.pipeline.multi_source_merge import MergedCandidate
                return [
                    MergedCandidate(
                        title="Soap With Signal",
                        tmdb_id=11,
                        imdb_id="tt0000011",
                        media_type="tv",
                        fp_items=[{"ranking": 1, "platform": "netflix", "days_total": 5}],
                        tmdb_data={
                            "popularity": 100,
                            "vote_average": 7,
                            "vote_count": 500,
                            "genres": [{"id": 10766, "name": "Soap"}],
                        },
                        trakt_data=None,
                        source_flags={"flixpatrol"},
                    ),
                ]

            def mock_resolve_source_dates(*args, **kwargs):
                return {"flixpatrol": "2026-05-13", "tmdb": "2026-05-13", "trakt": "2026-05-13"}

            with patch("movietrace.pipeline.discovery._load_secrets", return_value={"omdb": {}, "tmdb": {}}):
                with patch("movietrace.pipeline.discovery._ensure_fp_data",
                           return_value={"planned_calls": 0, "actual_calls": 0}):
                    with patch("movietrace.pipeline.discovery._resolve_source_dates_with_fallback",
                               side_effect=mock_resolve_source_dates):
                        with patch("movietrace.pipeline.multi_source_merge.merge_three_sources",
                                   side_effect=mock_merge):
                            result = run_discovery(date_from="2026-05-13", dry_run=True, db_path=db_path)

            stats = result.get("stats", {})
            assert stats.get("soap_pure_fallback_suppressed", 0) == 0
            # Soap with fresh signal passes through
            candidates = result.get("candidates", [])
            assert len(candidates) >= 1
            assert candidates[0].get("is_soap") is True
        finally:
            os.unlink(db_path)


# ── P1.57e: _write_current_discovery_batch unit tests ──────────────────


def _seed_canonical_for_batch(conn, tmdb_id: int, media_type: str) -> int:
    """Insert a minimal canonical_item + external_ids row, return canonical_item_id."""
    content_type = "tv" if media_type in ("tv", "show") else "movie"
    key = f"tmdb:{content_type}:{tmdb_id}"
    cursor = conn.execute(
        """INSERT INTO canonical_items
           (canonical_item_key, title, content_type, content_granularity)
           VALUES (?, ?, ?, ?)""",
        (key, f"Title {tmdb_id}", content_type, content_type),
    )
    cid = cursor.lastrowid
    ext_id = f"{content_type}:{tmdb_id}"
    conn.execute(
        "INSERT INTO external_ids (canonical_item_id, source, external_id) VALUES (?, 'tmdb', ?)",
        (cid, ext_id),
    )
    conn.commit()
    return cid


class TestWriteCurrentDiscoveryBatch:
    """Unit tests for _write_current_discovery_batch (P1.57e)."""

    def _make_db(self):
        from movietrace.db.schema import initialize_database
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        initialize_database(db_path)
        conn = sqlite3.connect(db_path)
        conn.execute("pragma foreign_keys = on")
        return conn, db_path

    def _candidate(self, tmdb_id: int, media_type: str = "movie", has_fresh_signal: bool = True):
        return {
            "tmdb_id": tmdb_id,
            "media_type": media_type,
            "title": f"Title {tmdb_id}",
            "hot_score": 80.0,
            "priority": "P1",
            "has_fresh_signal": has_fresh_signal,
            "tmdb_data": {"popularity": 200.0, "vote_average": 7.5, "vote_count": 1000, "genres": []},
            "fp_items": [],
            "score_breakdown": {"flixpatrol_score": 50.0},
        }

    def test_eligible_candidate_creates_item_and_observation(self):
        conn, db_path = self._make_db()
        try:
            _seed_canonical_for_batch(conn, 1001, "movie")
            cand = self._candidate(1001, "movie")
            stats = _write_current_discovery_batch(conn, [cand], "2026-05-20")
            conn.commit()
            assert stats["created"] == 1
            assert stats["observations_written"] == 1
            assert stats["skipped_source_date_fallback"] == 0
            item = conn.execute(
                "SELECT discovery_key, latest_hot_score FROM current_discovery_items"
            ).fetchone()
            assert item is not None
            assert item[0] == "discovery:movie:1001"
            assert abs(item[1] - 80.0) < 0.01
            obs = conn.execute(
                "SELECT hot_score FROM discovery_observations WHERE discovery_key='discovery:movie:1001'"
            ).fetchone()
            assert obs is not None
        finally:
            conn.close()
            os.unlink(db_path)

    def test_pure_fallback_candidate_skipped(self):
        conn, db_path = self._make_db()
        try:
            _seed_canonical_for_batch(conn, 1002, "tv")
            cand = self._candidate(1002, "tv", has_fresh_signal=False)
            stats = _write_current_discovery_batch(conn, [cand], "2026-05-20")
            conn.commit()
            assert stats["skipped_source_date_fallback"] == 1
            assert stats["created"] == 0
            assert stats["observations_written"] == 0
            count = conn.execute(
                "SELECT count(*) FROM current_discovery_items"
            ).fetchone()[0]
            assert count == 0
        finally:
            conn.close()
            os.unlink(db_path)

    def test_second_call_same_date_counts_as_updated(self):
        conn, db_path = self._make_db()
        try:
            _seed_canonical_for_batch(conn, 1003, "tv")
            cand = self._candidate(1003, "tv")
            stats1 = _write_current_discovery_batch(conn, [cand], "2026-05-20")
            conn.commit()
            assert stats1["created"] == 1
            cand["hot_score"] = 90.0
            stats2 = _write_current_discovery_batch(conn, [cand], "2026-05-20")
            conn.commit()
            assert stats2["updated"] == 1
            assert stats2["created"] == 0
        finally:
            conn.close()
            os.unlink(db_path)

    def test_observation_idempotent_same_date(self):
        conn, db_path = self._make_db()
        try:
            _seed_canonical_for_batch(conn, 1004, "movie")
            cand = self._candidate(1004, "movie")
            _write_current_discovery_batch(conn, [cand], "2026-05-20")
            conn.commit()
            cand["hot_score"] = 95.0
            _write_current_discovery_batch(conn, [cand], "2026-05-20")
            conn.commit()
            count = conn.execute(
                "SELECT count(*) FROM discovery_observations WHERE discovery_key='discovery:movie:1004'"
            ).fetchone()[0]
            assert count == 1
        finally:
            conn.close()
            os.unlink(db_path)

    def test_tv_media_type_normalised_to_tv(self):
        conn, db_path = self._make_db()
        try:
            _seed_canonical_for_batch(conn, 1005, "tv")
            cand = self._candidate(1005, "tv")
            stats = _write_current_discovery_batch(conn, [cand], "2026-05-20")
            conn.commit()
            assert stats["created"] == 1
            key = conn.execute(
                "SELECT discovery_key FROM current_discovery_items"
            ).fetchone()[0]
            assert key == "discovery:tv:1005"
        finally:
            conn.close()
            os.unlink(db_path)

    def test_mixed_eligible_and_fallback(self):
        conn, db_path = self._make_db()
        try:
            _seed_canonical_for_batch(conn, 2001, "movie")
            _seed_canonical_for_batch(conn, 2002, "movie")
            candidates = [
                self._candidate(2001, "movie", has_fresh_signal=True),
                self._candidate(2002, "movie", has_fresh_signal=False),
            ]
            stats = _write_current_discovery_batch(conn, candidates, "2026-05-21")
            conn.commit()
            assert stats["created"] == 1
            assert stats["skipped_source_date_fallback"] == 1
            assert stats["observations_written"] == 1
        finally:
            conn.close()
            os.unlink(db_path)

    def test_no_canonical_id_skips_and_increments_stat(self):
        """A2: candidate without canonical_item registration is skipped;
        stat skipped_no_canonical_id must be incremented; no DB row written."""
        conn, db_path = self._make_db()
        try:
            # Do NOT seed canonical for tmdb_id=9999 — no external_ids row
            cand = self._candidate(9999, "movie")
            stats = _write_current_discovery_batch(conn, [cand], "2026-05-20")
            conn.commit()
            # Must skip and count it
            assert stats["skipped_no_canonical_id"] == 1
            # Must not write any DB row
            count = conn.execute(
                "SELECT count(*) FROM current_discovery_items"
            ).fetchone()[0]
            assert count == 0, "No row must be written when canonical_id is None"
            obs_count = conn.execute(
                "SELECT count(*) FROM discovery_observations"
            ).fetchone()[0]
            assert obs_count == 0
        finally:
            conn.close()
            os.unlink(db_path)

    def test_no_canonical_id_stat_key_present_by_default(self):
        """A2: skipped_no_canonical_id stat key must be present even when zero."""
        conn, db_path = self._make_db()
        try:
            _seed_canonical_for_batch(conn, 3001, "movie")
            cand = self._candidate(3001, "movie")
            stats = _write_current_discovery_batch(conn, [cand], "2026-05-20")
            assert "skipped_no_canonical_id" in stats
            assert stats["skipped_no_canonical_id"] == 0
        finally:
            conn.close()
            os.unlink(db_path)


# ── P1.57e: run_discovery commit/dry-run integration tests ─────────────


class TestRunDiscoveryCurrentDualWrite:
    """Integration tests for dual-write path via run_discovery (P1.57e)."""

    def _setup_db_with_fp(self, db_path: str, snapshot_date: str):
        from movietrace.db.schema import initialize_database
        initialize_database(db_path)
        conn = sqlite3.connect(db_path)
        conn.execute(
            """INSERT INTO flixpatrol_top10
               (fp_id, title, content_type, platform, country,
                snapshot_date, ranking, raw_payload_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            ("fp1", "Test Movie", "movie", "netflix", "united-states",
             snapshot_date, 1, "{}"),
        )
        conn.commit()
        conn.close()

    def _make_merged_candidate(self, tmdb_id: int, media_type: str = "movie"):
        from movietrace.pipeline.multi_source_merge import MergedCandidate
        return MergedCandidate(
            tmdb_id=tmdb_id,
            imdb_id=None,
            title=f"Title {tmdb_id}",
            media_type=media_type,
            fp_items=[{"platform": "netflix", "ranking": 1, "days_total": 5,
                       "snapshot_date": "2026-05-20"}],
            tmdb_data={
                "tmdb_id": tmdb_id,
                "popularity": 300.0,
                "vote_average": 8.0,
                "vote_count": 2000,
                "genres": [],
                "original_language": "en",
            },
            trakt_data=None,
            source_flags={"flixpatrol"},
        )

    def test_commit_mode_writes_current_discovery_and_observation(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            self._setup_db_with_fp(db_path, "2026-05-20")
            mc = self._make_merged_candidate(9001, "movie")

            def mock_merge(*args, **kwargs):
                return [mc]

            def mock_resolve_source_dates(*args, **kwargs):
                return {"flixpatrol": "2026-05-20", "tmdb": "2026-05-20", "trakt": "2026-05-20"}

            with patch("movietrace.pipeline.discovery._load_secrets",
                       return_value={"omdb": {}, "tmdb": {}}):
                with patch("movietrace.pipeline.discovery._ensure_fp_data",
                           return_value={"planned_calls": 0, "actual_calls": 0}):
                    with patch("movietrace.pipeline.discovery._resolve_source_dates_with_fallback",
                               side_effect=mock_resolve_source_dates):
                        with patch("movietrace.pipeline.multi_source_merge.merge_three_sources",
                                   side_effect=mock_merge):
                            result = run_discovery(
                                date_from="2026-05-20", dry_run=False, db_path=db_path
                            )

            stats = result.get("stats", {})
            conn = sqlite3.connect(db_path)
            cd_count = conn.execute("SELECT count(*) FROM current_discovery_items").fetchone()[0]
            obs_count = conn.execute("SELECT count(*) FROM discovery_observations").fetchone()[0]
            conn.close()

            assert cd_count >= 1, "commit mode should write current_discovery_items"
            assert obs_count >= 1, "commit mode should write discovery_observations"
            assert "current_discovery_created" in stats
            assert "observations_written" in stats
        finally:
            os.unlink(db_path)

    def test_dry_run_does_not_write_current_discovery(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            self._setup_db_with_fp(db_path, "2026-05-20")
            mc = self._make_merged_candidate(9002, "tv")

            def mock_merge(*args, **kwargs):
                return [mc]

            def mock_resolve_source_dates(*args, **kwargs):
                return {"flixpatrol": "2026-05-20", "tmdb": "2026-05-20", "trakt": "2026-05-20"}

            with patch("movietrace.pipeline.discovery._load_secrets",
                       return_value={"omdb": {}, "tmdb": {}}):
                with patch("movietrace.pipeline.discovery._ensure_fp_data",
                           return_value={"planned_calls": 0, "actual_calls": 0}):
                    with patch("movietrace.pipeline.discovery._resolve_source_dates_with_fallback",
                               side_effect=mock_resolve_source_dates):
                        with patch("movietrace.pipeline.multi_source_merge.merge_three_sources",
                                   side_effect=mock_merge):
                            result = run_discovery(
                                date_from="2026-05-20", dry_run=True, db_path=db_path
                            )

            conn = sqlite3.connect(db_path)
            cd_count = conn.execute("SELECT count(*) FROM current_discovery_items").fetchone()[0]
            obs_count = conn.execute("SELECT count(*) FROM discovery_observations").fetchone()[0]
            conn.close()

            assert cd_count == 0, "dry_run must not write current_discovery_items"
            assert obs_count == 0, "dry_run must not write discovery_observations"
            assert "current_discovery_created" not in result.get("stats", {})
        finally:
            os.unlink(db_path)

    def test_commit_mode_does_not_write_new_discovery_to_content_updates(self):
        """P1.57i: run_discovery commit mode must NOT write new_discovery rows to content_updates."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            self._setup_db_with_fp(db_path, "2026-05-20")
            mc = self._make_merged_candidate(9010, "movie")

            def mock_merge(*args, **kwargs):
                return [mc]

            def mock_resolve_source_dates(*args, **kwargs):
                return {"flixpatrol": "2026-05-20", "tmdb": "2026-05-20", "trakt": "2026-05-20"}

            with patch("movietrace.pipeline.discovery._load_secrets",
                       return_value={"omdb": {}, "tmdb": {}}):
                with patch("movietrace.pipeline.discovery._ensure_fp_data",
                           return_value={"planned_calls": 0, "actual_calls": 0}):
                    with patch("movietrace.pipeline.discovery._resolve_source_dates_with_fallback",
                               side_effect=mock_resolve_source_dates):
                        with patch("movietrace.pipeline.multi_source_merge.merge_three_sources",
                                   side_effect=mock_merge):
                            run_discovery(date_from="2026-05-20", dry_run=False, db_path=db_path)

            conn = sqlite3.connect(db_path)
            nd_count = conn.execute(
                "SELECT count(*) FROM content_updates WHERE update_type='new_discovery'"
            ).fetchone()[0]
            cd_count = conn.execute("SELECT count(*) FROM current_discovery_items").fetchone()[0]
            obs_count = conn.execute("SELECT count(*) FROM discovery_observations").fetchone()[0]
            conn.close()

            assert nd_count == 0, (
                f"P1.57i: new_discovery rows must not be written to content_updates, found {nd_count}"
            )
            assert cd_count >= 1, "current_discovery_items should still be written"
            assert obs_count >= 1, "discovery_observations should still be written"
        finally:
            os.unlink(db_path)

    def test_commit_mode_stats_include_current_discovery_fields(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            self._setup_db_with_fp(db_path, "2026-05-20")
            mc = self._make_merged_candidate(9003, "movie")

            def mock_merge(*args, **kwargs):
                return [mc]

            def mock_resolve_source_dates(*args, **kwargs):
                return {"flixpatrol": "2026-05-20", "tmdb": "2026-05-20", "trakt": "2026-05-20"}

            with patch("movietrace.pipeline.discovery._load_secrets",
                       return_value={"omdb": {}, "tmdb": {}}):
                with patch("movietrace.pipeline.discovery._ensure_fp_data",
                           return_value={"planned_calls": 0, "actual_calls": 0}):
                    with patch("movietrace.pipeline.discovery._resolve_source_dates_with_fallback",
                               side_effect=mock_resolve_source_dates):
                        with patch("movietrace.pipeline.multi_source_merge.merge_three_sources",
                                   side_effect=mock_merge):
                            result = run_discovery(
                                date_from="2026-05-20", dry_run=False, db_path=db_path
                            )

            stats = result.get("stats", {})
            for key in ("current_discovery_created", "current_discovery_updated",
                        "observations_written", "observations_skipped_internal_fallback_guard"):
                assert key in stats, f"stats missing key: {key}"
        finally:
            os.unlink(db_path)


# ── P1.57j: _should_skip_enrichment unit tests ────────────────────────────────


def _make_current_discovery_db() -> tuple[sqlite3.Connection, str]:
    """Create a file DB with the current_discovery_items schema."""
    from movietrace.db.schema import initialize_database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    initialize_database(db_path)
    conn = sqlite3.connect(db_path)
    conn.execute("pragma foreign_keys = on")
    return conn, db_path


def _insert_current_discovery_item(conn: sqlite3.Connection, discovery_key: str, content_type: str, tmdb_id: int) -> None:
    """Insert a minimal current_discovery_items row."""
    conn.execute(
        """INSERT INTO current_discovery_items
           (discovery_key, content_type, tmdb_id, first_discovered_date, last_discovered_date)
           VALUES (?, ?, ?, '2026-05-01', '2026-05-01')""",
        (discovery_key, content_type, tmdb_id),
    )
    conn.commit()


def _make_movie_candidate(tmdb_id: int, tmdb_data: dict | None = None) -> MergedCandidate:
    return MergedCandidate(
        tmdb_id=tmdb_id,
        imdb_id=None,
        title=f"Movie {tmdb_id}",
        media_type="movie",
        tmdb_data=tmdb_data or {},
    )


def _make_tv_candidate(tmdb_id: int, tmdb_data: dict | None = None) -> MergedCandidate:
    return MergedCandidate(
        tmdb_id=tmdb_id,
        imdb_id=None,
        title=f"TV {tmdb_id}",
        media_type="tv",
        tmdb_data=tmdb_data or {},
    )


class TestShouldSkipEnrichment:
    """P1.57j: _should_skip_enrichment unit tests covering all acceptance criteria."""

    # AC1: First-time discovery → False (no existing current_discovery_items row)
    def test_first_discovery_movie_returns_false(self):
        conn, db_path = _make_current_discovery_db()
        try:
            c = _make_movie_candidate(
                1001,
                {"original_language": "en", "release_date": "2024-01-01"},
            )
            assert _should_skip_enrichment(c, conn) is False
        finally:
            conn.close()
            os.unlink(db_path)

    def test_first_discovery_tv_returns_false(self):
        conn, db_path = _make_current_discovery_db()
        try:
            c = _make_tv_candidate(
                2001,
                {"original_language": "en", "last_air_date": "2024-01-01"},
            )
            assert _should_skip_enrichment(c, conn) is False
        finally:
            conn.close()
            os.unlink(db_path)

    # AC2: Repeat hit + metadata sufficient → True
    def test_repeat_hit_movie_sufficient_metadata_returns_true(self):
        conn, db_path = _make_current_discovery_db()
        try:
            _insert_current_discovery_item(conn, "discovery:movie:1002", "movie", 1002)
            c = _make_movie_candidate(
                1002,
                {"original_language": "en", "release_date": "2024-06-01"},
            )
            assert _should_skip_enrichment(c, conn) is True
        finally:
            conn.close()
            os.unlink(db_path)

    def test_repeat_hit_movie_movie_release_date_also_sufficient(self):
        conn, db_path = _make_current_discovery_db()
        try:
            _insert_current_discovery_item(conn, "discovery:movie:1003", "movie", 1003)
            c = _make_movie_candidate(
                1003,
                {"original_language": "ko", "movie_release_date": "2024-03-15"},
            )
            assert _should_skip_enrichment(c, conn) is True
        finally:
            conn.close()
            os.unlink(db_path)

    def test_repeat_hit_tv_last_air_date_sufficient(self):
        conn, db_path = _make_current_discovery_db()
        try:
            _insert_current_discovery_item(conn, "discovery:tv:2002", "tv", 2002)
            c = _make_tv_candidate(
                2002,
                {"original_language": "ja", "last_air_date": "2024-05-01"},
            )
            assert _should_skip_enrichment(c, conn) is True
        finally:
            conn.close()
            os.unlink(db_path)

    def test_repeat_hit_tv_last_episode_air_date_sufficient(self):
        conn, db_path = _make_current_discovery_db()
        try:
            _insert_current_discovery_item(conn, "discovery:tv:2003", "tv", 2003)
            c = _make_tv_candidate(
                2003,
                {"original_language": "zh", "last_episode_air_date": "2024-05-10"},
            )
            assert _should_skip_enrichment(c, conn) is True
        finally:
            conn.close()
            os.unlink(db_path)

    def test_repeat_hit_tv_last_episode_to_air_air_date_sufficient(self):
        conn, db_path = _make_current_discovery_db()
        try:
            _insert_current_discovery_item(conn, "discovery:tv:2004", "tv", 2004)
            c = _make_tv_candidate(
                2004,
                {
                    "original_language": "en",
                    "last_episode_to_air": {"air_date": "2024-04-20", "episode_number": 5},
                },
            )
            assert _should_skip_enrichment(c, conn) is True
        finally:
            conn.close()
            os.unlink(db_path)

    # AC3: Repeat hit + metadata insufficient → False
    def test_repeat_hit_missing_original_language_returns_false(self):
        conn, db_path = _make_current_discovery_db()
        try:
            _insert_current_discovery_item(conn, "discovery:movie:1004", "movie", 1004)
            c = _make_movie_candidate(
                1004,
                {"release_date": "2024-01-01"},  # no original_language
            )
            assert _should_skip_enrichment(c, conn) is False
        finally:
            conn.close()
            os.unlink(db_path)

    def test_repeat_hit_movie_missing_date_returns_false(self):
        conn, db_path = _make_current_discovery_db()
        try:
            _insert_current_discovery_item(conn, "discovery:movie:1005", "movie", 1005)
            c = _make_movie_candidate(
                1005,
                {"original_language": "en"},  # no date
            )
            assert _should_skip_enrichment(c, conn) is False
        finally:
            conn.close()
            os.unlink(db_path)

    def test_repeat_hit_tv_missing_all_dates_returns_false(self):
        conn, db_path = _make_current_discovery_db()
        try:
            _insert_current_discovery_item(conn, "discovery:tv:2005", "tv", 2005)
            c = _make_tv_candidate(
                2005,
                {"original_language": "en"},  # no date fields
            )
            assert _should_skip_enrichment(c, conn) is False
        finally:
            conn.close()
            os.unlink(db_path)

    def test_repeat_hit_empty_tmdb_data_returns_false(self):
        conn, db_path = _make_current_discovery_db()
        try:
            _insert_current_discovery_item(conn, "discovery:movie:1006", "movie", 1006)
            c = _make_movie_candidate(1006, {})
            assert _should_skip_enrichment(c, conn) is False
        finally:
            conn.close()
            os.unlink(db_path)

    def test_repeat_hit_none_tmdb_data_returns_false(self):
        conn, db_path = _make_current_discovery_db()
        try:
            _insert_current_discovery_item(conn, "discovery:movie:1007", "movie", 1007)
            c = _make_movie_candidate(1007, None)
            assert _should_skip_enrichment(c, conn) is False
        finally:
            conn.close()
            os.unlink(db_path)

    # Edge: no tmdb_id → False
    def test_no_tmdb_id_returns_false(self):
        conn, db_path = _make_current_discovery_db()
        try:
            c = MergedCandidate(
                tmdb_id=None,
                imdb_id=None,
                title="No ID",
                media_type="movie",
                tmdb_data={"original_language": "en", "release_date": "2024-01-01"},
            )
            assert _should_skip_enrichment(c, conn) is False
        finally:
            conn.close()
            os.unlink(db_path)

    # show media_type normalised to tv namespace
    def test_show_media_type_normalised_to_tv_namespace(self):
        conn, db_path = _make_current_discovery_db()
        try:
            _insert_current_discovery_item(conn, "discovery:tv:3001", "tv", 3001)
            c = MergedCandidate(
                tmdb_id=3001,
                imdb_id=None,
                title="Show 3001",
                media_type="show",
                tmdb_data={"original_language": "en", "last_air_date": "2024-05-01"},
            )
            assert _should_skip_enrichment(c, conn) is True
        finally:
            conn.close()
            os.unlink(db_path)


# ── P1.57j: stats include repeat_hit_enrichment_skipped ──────────────────────


class TestRepeatHitEnrichmentSkippedStat:
    """AC5: stats includes repeat_hit_enrichment_skipped field."""

    def _make_merged_candidate(self, tmdb_id: int, media_type: str = "movie"):
        return MergedCandidate(
            tmdb_id=tmdb_id,
            imdb_id=None,
            title=f"Title {tmdb_id}",
            media_type=media_type,
            fp_items=[{"platform": "netflix", "ranking": 1, "days_total": 5}],
            tmdb_data={
                "tmdb_id": tmdb_id,
                "popularity": 300.0,
                "vote_average": 8.0,
                "vote_count": 2000,
                "genres": [],
                "original_language": "en",
                "release_date": "2024-01-01",
            },
            trakt_data=None,
            source_flags={"flixpatrol"},
        )

    def _setup_db_with_fp(self, db_path: str, snapshot_date: str):
        from movietrace.db.schema import initialize_database
        initialize_database(db_path)
        conn = sqlite3.connect(db_path)
        conn.execute(
            """INSERT INTO flixpatrol_top10
               (fp_id, title, content_type, platform, country,
                snapshot_date, ranking, raw_payload_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            ("fp1", "Test Movie", "movie", "netflix", "united-states",
             snapshot_date, 1, "{}"),
        )
        conn.commit()
        conn.close()

    def test_stats_always_contain_repeat_hit_enrichment_skipped(self):
        """dry_run: stats must include repeat_hit_enrichment_skipped >= 0."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            self._setup_db_with_fp(db_path, "2026-05-22")
            mc = self._make_merged_candidate(8001, "movie")

            def mock_merge(*args, **kwargs):
                return [mc]

            def mock_resolve_source_dates(*args, **kwargs):
                return {"flixpatrol": "2026-05-22", "tmdb": "2026-05-22", "trakt": "2026-05-22"}

            with patch("movietrace.pipeline.discovery._load_secrets",
                       return_value={"omdb": {}, "tmdb": {}}):
                with patch("movietrace.pipeline.discovery._ensure_fp_data",
                           return_value={"planned_calls": 0, "actual_calls": 0}):
                    with patch("movietrace.pipeline.discovery._resolve_source_dates_with_fallback",
                               side_effect=mock_resolve_source_dates):
                        with patch("movietrace.pipeline.multi_source_merge.merge_three_sources",
                                   side_effect=mock_merge):
                            result = run_discovery(
                                date_from="2026-05-22", dry_run=True, db_path=db_path
                            )

            stats = result.get("stats", {})
            assert "repeat_hit_enrichment_skipped" in stats, (
                "stats must contain repeat_hit_enrichment_skipped"
            )
            # First-time discovery: no existing current_discovery_items → 0 skipped
            assert stats["repeat_hit_enrichment_skipped"] == 0
        finally:
            os.unlink(db_path)

    def test_repeat_hit_candidate_counted_in_skipped_stat(self):
        """commit mode: pre-seeded current_discovery_items entry → skipped == 1."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            self._setup_db_with_fp(db_path, "2026-05-22")
            # Pre-seed: this candidate is already a known discovery
            conn = sqlite3.connect(db_path)
            conn.execute(
                """INSERT INTO current_discovery_items
                   (discovery_key, content_type, tmdb_id, first_discovered_date, last_discovered_date)
                   VALUES ('discovery:movie:8002', 'movie', 8002, '2026-05-21', '2026-05-21')"""
            )
            conn.commit()
            conn.close()

            mc = self._make_merged_candidate(8002, "movie")

            def mock_merge(*args, **kwargs):
                return [mc]

            def mock_resolve_source_dates(*args, **kwargs):
                return {"flixpatrol": "2026-05-22", "tmdb": "2026-05-22", "trakt": "2026-05-22"}

            with patch("movietrace.pipeline.discovery._load_secrets",
                       return_value={"omdb": {}, "tmdb": {}}):
                with patch("movietrace.pipeline.discovery._ensure_fp_data",
                           return_value={"planned_calls": 0, "actual_calls": 0}):
                    with patch("movietrace.pipeline.discovery._resolve_source_dates_with_fallback",
                               side_effect=mock_resolve_source_dates):
                        with patch("movietrace.pipeline.multi_source_merge.merge_three_sources",
                                   side_effect=mock_merge):
                            result = run_discovery(
                                date_from="2026-05-22", dry_run=False, db_path=db_path
                            )

            stats = result.get("stats", {})
            assert stats.get("repeat_hit_enrichment_skipped") == 1, (
                f"Expected 1 skipped, got {stats.get('repeat_hit_enrichment_skipped')}"
            )
        finally:
            os.unlink(db_path)


# ── B2: _should_skip_enrichment stable_metadata fallback tests ─────────────────


class TestShouldSkipEnrichmentStableMetadataFallback:
    """B2: TV repeat hit + TMDb trending missing last_air_date → fallback to stable_metadata."""

    def test_tv_repeat_hit_tmdb_data_missing_date_stable_meta_has_date_returns_true(self):
        """TV repeat hit + tmdb_data lacks last_air_date + stable_metadata has it → True."""
        conn, db_path = _make_current_discovery_db()
        try:
            import json as _json
            stable_meta = _json.dumps(
                {"original_language": "en", "last_air_date": "2024-06-01"}, ensure_ascii=False
            )
            conn.execute(
                """INSERT INTO current_discovery_items
                   (discovery_key, content_type, tmdb_id,
                    first_discovered_date, last_discovered_date, stable_metadata_json)
                   VALUES ('discovery:tv:9001', 'tv', 9001,
                           '2026-05-01', '2026-05-01', ?)""",
                (stable_meta,),
            )
            conn.commit()
            # candidate has no last_air_date in tmdb_data (TMDb trending typical case)
            c = _make_tv_candidate(9001, {"original_language": "en"})
            assert _should_skip_enrichment(c, conn) is True
        finally:
            conn.close()
            os.unlink(db_path)

    def test_tv_repeat_hit_both_missing_date_returns_false(self):
        """TV repeat hit + tmdb_data no date + stable_metadata also no date → False."""
        conn, db_path = _make_current_discovery_db()
        try:
            import json as _json
            stable_meta = _json.dumps(
                {"original_language": "en"}, ensure_ascii=False
            )
            conn.execute(
                """INSERT INTO current_discovery_items
                   (discovery_key, content_type, tmdb_id,
                    first_discovered_date, last_discovered_date, stable_metadata_json)
                   VALUES ('discovery:tv:9002', 'tv', 9002,
                           '2026-05-01', '2026-05-01', ?)""",
                (stable_meta,),
            )
            conn.commit()
            c = _make_tv_candidate(9002, {"original_language": "en"})
            assert _should_skip_enrichment(c, conn) is False
        finally:
            conn.close()
            os.unlink(db_path)

    def test_tv_repeat_hit_no_stable_meta_row_returns_false(self):
        """TV repeat hit + tmdb_data no date + no stable_metadata (NULL) → False."""
        conn, db_path = _make_current_discovery_db()
        try:
            # stable_metadata_json is NULL (default)
            _insert_current_discovery_item(conn, "discovery:tv:9003", "tv", 9003)
            c = _make_tv_candidate(9003, {"original_language": "en"})
            assert _should_skip_enrichment(c, conn) is False
        finally:
            conn.close()
            os.unlink(db_path)

    def test_tv_repeat_hit_stable_meta_also_provides_language_returns_true(self):
        """TV repeat hit + tmdb_data empty + stable_metadata has language+date → True."""
        conn, db_path = _make_current_discovery_db()
        try:
            import json as _json
            stable_meta = _json.dumps(
                {"original_language": "ko", "last_air_date": "2024-03-15"}, ensure_ascii=False
            )
            conn.execute(
                """INSERT INTO current_discovery_items
                   (discovery_key, content_type, tmdb_id,
                    first_discovered_date, last_discovered_date, stable_metadata_json)
                   VALUES ('discovery:tv:9004', 'tv', 9004,
                           '2026-05-01', '2026-05-01', ?)""",
                (stable_meta,),
            )
            conn.commit()
            # tmdb_data completely empty
            c = _make_tv_candidate(9004, {})
            assert _should_skip_enrichment(c, conn) is True
        finally:
            conn.close()
            os.unlink(db_path)
