import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


class TestRenderScoringRules(unittest.TestCase):
    def test_render_scoring_rules_contains_weights(self):
        from movietrace.reports.export_writer import _render_scoring_rules
        from movietrace.pipeline.scoring import DEFAULT_WEIGHTS
        lines = _render_scoring_rules()
        text = "\n".join(lines)
        weights = DEFAULT_WEIGHTS.get("weights", {})
        # At least one weight percentage should appear
        for key, val in weights.items():
            pct = f"{val * 100:.0f}%"
            self.assertIn(pct, text, f"Expected weight {pct} for {key} in output")
            break
        self.assertIn("⚖️ 评分规则与权重", text)
        self.assertIn("阈值", text)


class TestRenderFunnel(unittest.TestCase):
    def test_render_funnel_shows_filtered_count(self):
        from movietrace.reports.export_writer import _render_funnel
        stats = {
            "total_merged": 150,
            "total_passed": 30,
            "filtered_out": [
                {"title": "Show A", "hot_score": 49.9, "content_type": "tv"},
                {"title": "Show B", "hot_score": 45.0, "content_type": "movie"},
            ],
        }
        lines = _render_funnel(stats)
        text = "\n".join(lines)
        self.assertIn("150", text)
        self.assertIn("30", text)
        self.assertIn("120", text)  # eliminated count
        self.assertIn("Show A", text)
        self.assertIn("🔍 过滤明细", text)

    def test_render_funnel_returns_empty_when_no_stats(self):
        from movietrace.reports.export_writer import _render_funnel
        self.assertEqual(_render_funnel(None), [])


class TestRenderErrors(unittest.TestCase):
    def test_render_errors_empty(self):
        from movietrace.reports.export_writer import _render_errors
        lines = _render_errors([])
        text = "\n".join(lines)
        self.assertIn("本次运行无异常 ✓", text)
        self.assertIn("⚠️ 异常", text)

    def test_render_errors_with_failures(self):
        import json
        from movietrace.reports.export_writer import _render_errors
        source_summary = json.dumps({
            "source_data_status": {
                "tmdb": {"status": "fallback", "snapshot_date": "2026-05-17"},
            }
        })
        updates = [{"source_summary_json": source_summary}]
        lines = _render_errors(updates)
        text = "\n".join(lines)
        self.assertIn("TMDb", text)
        self.assertIn("fallback", text)


if __name__ == "__main__":
    unittest.main()
