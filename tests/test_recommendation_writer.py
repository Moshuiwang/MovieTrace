from __future__ import annotations

import json
import sqlite3
import tempfile
from pathlib import Path

import pytest

from movietrace.feishu.recommendation_writer import (
    make_content_update_id,
    write_recommendations,
    _load_candidates_for_feishu,
    _write_audit_log,
)
from movietrace.db.schema import initialize_database


# ── make_content_update_id tests ────────────────────────────────────────


class TestMakeContentUpdateId:
    def test_discovery_when_not_in_baseline(self):
        cid = make_content_update_id(100, 1, False, "no_match")
        assert "#discovery#" in cid
        assert cid.startswith("100#")

    def test_existing_when_in_baseline(self):
        cid = make_content_update_id(200, 2, True, "high")
        assert "#existing#" in cid

    def test_pending_review_when_low_confidence(self):
        cid = make_content_update_id(300, 3, False, "low")
        assert "#pending_review#" in cid

    def test_pending_review_overrides_in_baseline(self):
        cid = make_content_update_id(400, 4, True, "low")
        assert "#pending_review#" in cid

    def test_fallback_to_candidate_id_when_no_canonical(self):
        cid = make_content_update_id(None, 42, False, "no_match")
        assert cid.startswith("c42#")


# ── Dry-run tests ───────────────────────────────────────────────────────


class TestWriteRecommendationsDryRun:
    def test_dry_run_generates_audit_log(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        import os
        try:
            conn = sqlite3.connect(db_path)
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

            # Seed data
            conn.execute(
                """insert into candidates
                   (title, content_type, hot_score, priority, discovery_source,
                    score_breakdown_json, reason_text, snapshot_date)
                   values ('Test Movie', 'movie', 75, 'P1', 'new_release', '{}', '', '2026-05-11')"""
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
                stats = write_recommendations(
                    dry_run=True, db_path=db_path, output_dir=tmpdir
                )
                assert stats["total"] == 1
                assert stats["insert"] == 1

                # Verify audit log
                log_files = list(Path(tmpdir).glob("*.jsonl"))
                assert len(log_files) == 1
                lines = log_files[0].read_text().strip().split("\n")
                assert len(lines) == 1
                entry = json.loads(lines[0])
                assert entry["action"] == "insert"
                assert "content_update_id" in entry
                assert "Test" in entry.get("title", "")
        finally:
            os.unlink(db_path)

    def test_empty_candidates_returns_zero(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        import os
        try:
            initialize_database(db_path)
            with tempfile.TemporaryDirectory() as tmpdir:
                stats = write_recommendations(dry_run=True, db_path=db_path, output_dir=tmpdir)
                assert stats["total"] == 0
        finally:
            os.unlink(db_path)


# ── Audit log tests ─────────────────────────────────────────────────────


class TestAuditLog:
    def test_writes_jsonl_entry(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            entry = {
                "timestamp": "2026-05-11T12:00:00Z",
                "action": "insert",
                "content_update_id": "1#discovery",
                "feishu_record_id": None,
                "status_code": 200,
                "reason": "Test entry",
            }
            _write_audit_log(entry, tmpdir)

            log_files = list(Path(tmpdir).glob("*.jsonl"))
            assert len(log_files) == 1
            line = log_files[0].read_text().strip()
            parsed = json.loads(line)
            assert parsed["action"] == "insert"
            assert parsed["content_update_id"] == "1#discovery"


# ── Integration test ────────────────────────────────────────────────────


class TestFullPipeline:
    def test_all_candidates_have_valid_content_update_ids(self):
        """Verify content_update_id uniqueness for all real candidates."""
        import sqlite3 as sq
        conn = sq.connect("data/movietrace.db")
        rows = conn.execute(
            """select c.id, cm.is_in_baseline, cm.match_confidence, cm.baseline_item_id
               from candidates c
               join candidate_matches cm on cm.candidate_id = c.id"""
        ).fetchall()
        conn.close()

        ids_set = set()
        for r in rows:
            cid = make_content_update_id(r[3], r[0], bool(r[1]), r[2])
            assert cid not in ids_set, f"Duplicate content_update_id: {cid}"
            ids_set.add(cid)

        assert len(ids_set) == len(rows), f"Expected {len(rows)} unique IDs, got {len(ids_set)}"
