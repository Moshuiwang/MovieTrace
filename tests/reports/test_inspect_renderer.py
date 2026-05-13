import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))


class InspectRendererTest(unittest.TestCase):
    def test_format_table_empty(self):
        from movietrace.reports.inspect_renderer import format_table
        result = format_table([])
        self.assertIn("No updates found", result)

    def test_format_table_with_data(self):
        from movietrace.reports.inspect_renderer import format_table
        updates = [{
            "priority": "P0", "update_type": "new_discovery", "title": "The Boys",
            "hot_score": 87.0,
            "source_summary_json": '{"fp":{"platform":"nf","ranking":1},"tmdb":{"popularity":500},"trakt":{"watchers":5000}}',
            "created_at": "2026-05-13 14:23",
        }]
        result = format_table(updates)
        self.assertIn("The Boys", result)
        self.assertIn("P0", result)
        self.assertIn("87.0", result)
        self.assertIn("new_discovery", result)
        self.assertIn("FP/TMDb/Trakt", result)

    def test_format_table_missing_source_json(self):
        from movietrace.reports.inspect_renderer import format_table
        updates = [{
            "priority": "P2", "update_type": "new_season", "title": "Test",
            "hot_score": 60.0, "source_summary_json": "",
            "created_at": "2026-05-13",
        }]
        result = format_table(updates)
        self.assertIn("Test", result)
        self.assertIn("(baseline)", result)

    def test_format_table_long_title_truncated(self):
        from movietrace.reports.inspect_renderer import format_table
        updates = [{
            "priority": "P1", "update_type": "new_discovery",
            "title": "This Is A Very Long Title That Exceeds Thirty Characters",
            "hot_score": 75.0, "source_summary_json": "{}",
            "created_at": "2026-05-13",
        }]
        result = format_table(updates)
        self.assertIn("…", result)

    def test_format_json_valid(self):
        import json
        from movietrace.reports.inspect_renderer import format_json_enhanced
        updates = [{
            "content_update_id": "discovery:100:2026-05-13",
            "update_type": "new_discovery", "priority": "P1",
            "hot_score": 78.0, "title": "Test", "source_summary_json": "{}",
            "created_at": "2026-05-13",
        }]
        result = format_json_enhanced(updates)
        data = json.loads(result)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["priority"], "P1")

    def test_format_detail_shows_all_fields(self):
        from movietrace.reports.inspect_renderer import format_detail
        update = {
            "content_update_id": "discovery:76479:2026-05-13",
            "title": "The Boys",
            "priority": "P0", "hot_score": 87.0,
            "update_type": "new_discovery",
            "created_at": "2026-05-13 14:23",
            "source_summary_json": '{"fp":{"platform":"netflix","ranking":1,"days_total":32},"tmdb":{"popularity":569.2,"vote_average":8.45,"vote_count":12247},"trakt":{"watchers":5520}}',
        }
        result = format_detail(update)
        self.assertIn("The Boys", result)
        self.assertIn("netflix", result)
        self.assertIn("569.2", result)
        self.assertIn("5520", result)


if __name__ == "__main__":
    unittest.main()
