"""Tests for movietrace.feedback.weekly_report."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))


def _sample_pull_data(hot_records=None, gap_records=None):
    return {
        "pulled_at": "2026-05-16T10:00:00+08:00",
        "hot_table": {
            "table_id": "tbl84xx4WNv54An9",
            "range_days": 7,
            "records": hot_records or [],
        },
        "gap_table": {
            "table_id": "tbl1NNU8kmlLKpLm",
            "records": gap_records or [],
        },
    }


def _hot(
    title="Test Show",
    priority="P1",
    hot_score=80.0,
    operator_status="待看",
    vendor_status="未提交",
    operator_note="",
):
    return {
        "record_id": "rec1",
        "content_update_id": "discovery:tv:1234:2026-05-15",
        "title": title,
        "discovery_date": "2026-05-15",
        "priority": priority,
        "hot_score": hot_score,
        "tmdb_id": "1234",
        "operator_status": operator_status,
        "operator_note": operator_note,
        "vendor_status": vendor_status,
        "assignee": "",
    }


def _gap(
    name="Gap Show",
    tmdb_id="5678",
    hot_score=60.0,
    gap_seasons="S4,S5",
    operator_status="待补",
    operator_note="",
):
    return {
        "record_id": "gap1",
        "tmdb_id": tmdb_id,
        "name": name,
        "hot_score": hot_score,
        "gap_count": 2,
        "gap_seasons": gap_seasons,
        "operator_status": operator_status,
        "operator_note": operator_note,
        "assignee": "",
    }


class TestGenerateWeeklyReport(unittest.TestCase):
    def _generate(self, pull_data):
        from movietrace.feedback.weekly_report import generate_weekly_report
        return generate_weekly_report(pull_data, db_path=None, dry_run=True)

    def test_report_contains_five_sections(self):
        pull = _sample_pull_data(
            hot_records=[_hot()],
            gap_records=[_gap()],
        )
        report = self._generate(pull)
        self.assertIn("## A. 基本信息", report)
        self.assertIn("## B. 热点发现表统计", report)
        self.assertIn("## C. A 库缺口表统计", report)
        self.assertIn("## D. 关键案例", report)
        self.assertIn("## E. V2 触发条件检查", report)

    def test_fill_rate_and_adopt_rate_empty_table(self):
        pull = _sample_pull_data()
        report = self._generate(pull)
        # No records → fill rate N/A, adopt rate N/A
        self.assertIn("N/A", report)

    def test_adopt_rate_computed_correctly(self):
        hot = [
            _hot(operator_status="确认加入"),
            _hot(operator_status="确认加入"),
            _hot(operator_status="不加入"),
        ]
        pull = _sample_pull_data(hot_records=hot)
        report = self._generate(pull)
        # adopted=2, decided=3 → 66.7%
        self.assertIn("66.7%", report)

    def test_zero_denominator_does_not_crash(self):
        pull = _sample_pull_data(gap_records=[])
        report = self._generate(pull)
        self.assertIn("N/A", report)

    def test_rejected_high_priority_case_listed(self):
        hot = [_hot(title="Miss Show", priority="P0", operator_status="不加入", operator_note="not for us")]
        pull = _sample_pull_data(hot_records=hot)
        report = self._generate(pull)
        self.assertIn("Miss Show", report)
        self.assertIn("not for us", report)

    def test_low_score_accepted_case_listed(self):
        hot = [_hot(title="Hidden Gem", hot_score=45.0, operator_status="确认加入")]
        pull = _sample_pull_data(hot_records=hot)
        report = self._generate(pull)
        self.assertIn("Hidden Gem", report)

    def test_iso_week_filename_format(self):
        from movietrace.feedback.weekly_report import generate_weekly_report
        import tempfile, os
        from datetime import datetime
        from zoneinfo import ZoneInfo
        pull = _sample_pull_data(hot_records=[_hot()], gap_records=[_gap()])
        with tempfile.TemporaryDirectory() as tmpdir:
            generate_weekly_report(pull, output_dir=tmpdir, db_path=None, dry_run=False)
            files = list(Path(tmpdir).glob("feedback_log_*.md"))
        self.assertEqual(len(files), 1)
        name = files[0].name
        # Format: feedback_log_YYYY-Www.md
        self.assertRegex(name, r"feedback_log_\d{4}-W\d{2}\.md")

    def test_gap_top10_pending_shown(self):
        gaps = [_gap(name=f"Show {i}", hot_score=float(100 - i), operator_status="待补") for i in range(12)]
        pull = _sample_pull_data(gap_records=gaps)
        report = self._generate(pull)
        # Top 10 of 12 — Show 0 (highest score) should appear
        self.assertIn("Show 0", report)

    def test_advance_rate_computed(self):
        gaps = [
            _gap(operator_status="已补"),
            _gap(operator_status="跳过"),
            _gap(operator_status="待补"),
            _gap(operator_status="待补"),
        ]
        pull = _sample_pull_data(gap_records=gaps)
        report = self._generate(pull)
        # advanced=2, total=4 → 50.0%
        self.assertIn("50.0%", report)


if __name__ == "__main__":
    unittest.main()
