from __future__ import annotations

import json
import sqlite3
import tempfile
from datetime import date
from pathlib import Path

import pytest

from movietrace.reports.daily_writer import (
    generate_daily_report,
    write_daily_report,
    _section_new,
    _section_existing,
    _section_review,
    _short_reason,
    _esc,
)


# ── Helpers ─────────────────────────────────────────────────────────────


def _make_row(**overrides):
    defaults = {
        "id": 1,
        "title": "Test Movie",
        "content_type": "movie",
        "hot_score": 75.0,
        "priority": "P1",
        "discovery_source": "new_release",
        "score_breakdown_json": json.dumps({"flixpatrol_score": 90}),
        "reason_text": "Test reason.",
        "snapshot_date": "2026-05-11",
        "tmdb_id": 123,
        "imdb_id": "tt456",
        "is_in_baseline": 0,
        "match_confidence": "no_match",
        "match_method": "no_match",
        "match_score_detail": 0.0,
        "requires_human_review": 0,
        "match_reason": "",
        "baseline_item_id": None,
        "baseline_title": None,
    }
    defaults.update(overrides)
    return defaults


def _seed_db(conn):
    schema_sql = (
        Path(__file__).parent.parent / "src/movietrace/db/schema.py"
    ).read_text()
    ddl_start = schema_sql.index('SCHEMA_SQL = """') + len('SCHEMA_SQL = """')
    ddl_end = schema_sql.index('"""', ddl_start)
    ddl = schema_sql[ddl_start:ddl_end]
    conn.executescript(ddl)
    conn.execute("insert or ignore into schema_migrations(version) values (1)")
    conn.commit()
    migrations_dir = Path(__file__).parent.parent / "src/movietrace/db/migrations"
    for fname in ["002_flixpatrol_top10.sql", "003_candidates.sql", "004_candidate_matches.sql"]:
        sql = (migrations_dir / fname).read_text()
        conn.executescript(sql)
        conn.execute(
            "insert or ignore into schema_migrations(version) values (?)",
            (int(fname[:3]),),
        )
        conn.commit()


# ── Unit tests ──────────────────────────────────────────────────────────


class TestShortReason:
    def test_high_fp_score(self):
        item = {"score_breakdown_json": json.dumps({"flixpatrol_score": 90})}
        reason = _short_reason(item)
        assert "FP热度高" in reason

    def test_medium_fp_score(self):
        item = {"score_breakdown_json": json.dumps({"flixpatrol_score": 60})}
        reason = _short_reason(item)
        assert "FP在榜" in reason

    def test_both_discovery(self):
        item = {
            "score_breakdown_json": json.dumps({"flixpatrol_score": 90}),
            "discovery_source": "both",
        }
        reason = _short_reason(item)
        assert len(reason) <= 60

    def test_fallback(self):
        item = {"score_breakdown_json": "{}"}
        reason = _short_reason(item)
        assert len(reason) > 0

    def test_max_60_chars(self):
        item = {
            "score_breakdown_json": json.dumps({
                "flixpatrol_score": 90,
                "tmdb_popularity_score": 95,
            }),
            "discovery_source": "both",
        }
        reason = _short_reason(item)
        assert len(reason) <= 60


class TestEsc:
    def test_escapes_pipe(self):
        assert _esc("a|b") == "a\\|b"

    def test_handles_none(self):
        assert _esc(None) == ""


class TestSections:
    def test_new_section_with_items(self):
        items = [_make_row(id=1, title="Movie A"), _make_row(id=2, title="Movie B")]
        lines = _section_new(items)
        assert len(lines) > 2
        assert "## 🆕" in "\n".join(lines) or "新发现" in "\n".join(lines)

    def test_new_section_empty(self):
        lines = _section_new([])
        assert any("暂无" in l for l in lines)

    def test_existing_section_with_items(self):
        items = [_make_row(id=1, is_in_baseline=1, match_confidence="high",
                           baseline_title="Original Title")]
        lines = _section_existing(items)
        assert "Original Title" in "\n".join(lines)

    def test_existing_section_empty(self):
        lines = _section_existing([])
        assert any("暂无" in l for l in lines)

    def test_review_section_with_items(self):
        items = [_make_row(id=1, match_confidence="low", match_score_detail=0.65,
                           match_method="edit_distance", baseline_item_id=5)]
        lines = _section_review(items)
        text = "\n".join(lines)
        assert "#5" in text or "5" in text

    def test_review_section_empty(self):
        lines = _section_review([])
        assert any("暂无" in l for l in lines)


class TestGenerateDailyReport:
    def test_full_report_generation(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        import os
        try:
            conn = sqlite3.connect(db_path)
            _seed_db(conn)

            # Seed candidates
            for i, row_data in enumerate([
                {"title": "New Hot Movie", "content_type": "movie", "hot_score": 82,
                 "priority": "P1", "discovery_source": "new_release"},
                {"title": "Existing Show", "content_type": "tv_show", "hot_score": 78,
                 "priority": "P1", "discovery_source": "global_hot"},
                {"title": "Maybe Match", "content_type": "movie", "hot_score": 55,
                 "priority": "P2", "discovery_source": "new_release"},
            ]):
                conn.execute(
                    """insert into candidates
                       (title, content_type, hot_score, priority, discovery_source,
                        score_breakdown_json, reason_text, snapshot_date)
                       values (?, ?, ?, ?, ?, ?, ?, '2026-05-11')""",
                    (row_data["title"], row_data["content_type"], row_data["hot_score"],
                     row_data["priority"], row_data["discovery_source"],
                     json.dumps({"flixpatrol_score": 80}), ""),
                )

            # Seed baseline
            conn.execute(
                """insert into baseline_items
                   (title, content_type, content_granularity, year, raw_fields_json, match_status)
                   values (?, ?, 'title', ?, '{}', 'unmatched')""",
                ("Existing Show", "tv_show", 2023),
            )

            # Seed candidate_matches
            matches = [
                (1, 0, None, "no_match", "no_match", 0.0, 0, ""),  # new
                (2, 1, 1, "high", "exact_title", 0.95, 0, ""),     # existing
                (3, 0, None, "low", "edit_distance", 0.65, 1, "fuzzy"),  # review
            ]
            for m in matches:
                conn.execute(
                    """insert into candidate_matches
                       (candidate_id, is_in_baseline, baseline_item_id, match_confidence,
                        match_method, match_score_detail, requires_human_review, reason_text)
                       values (?, ?, ?, ?, ?, ?, ?, ?)""",
                    m,
                )
            conn.commit()
            conn.close()

            report = generate_daily_report(date.today(), db_path)

            # Verify structure
            assert "# MovieTrace" in report
            assert "📊 统计汇总" in report
            assert "🆕 新发现" in report
            assert "♻️ 已有基线内容" in report
            assert "⚠️ 待人工确认" in report
            assert "1" in report  # counts

        finally:
            os.unlink(db_path)

    def test_empty_db_returns_empty_report(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        import os
        try:
            conn = sqlite3.connect(db_path)
            _seed_db(conn)
            conn.commit()
            conn.close()

            report = generate_daily_report(date.today(), db_path)
            assert "暂无候选数据" in report
        finally:
            os.unlink(db_path)


class TestWriteDailyReport:
    def test_writes_file(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        import os
        try:
            conn = sqlite3.connect(db_path)
            _seed_db(conn)
            conn.execute(
                """insert into candidates
                   (title, content_type, hot_score, priority, discovery_source,
                    score_breakdown_json, reason_text, snapshot_date)
                   values ('Test', 'movie', 50, 'P2', 'new_release', '{}', '', '2026-05-11')"""
            )
            conn.execute(
                """insert into candidate_matches
                   (candidate_id, is_in_baseline, match_confidence, match_method,
                    match_score_detail, requires_human_review, reason_text)
                   values (1, 0, 'no_match', 'no_match', 0, 0, '')"""
            )
            conn.commit()
            conn.close()

            with tempfile.TemporaryDirectory() as tmpdir:
                path = write_daily_report(date.today(), tmpdir, db_path)
                assert Path(path).exists()
                content = Path(path).read_text()
                assert "# MovieTrace" in content
        finally:
            os.unlink(db_path)
