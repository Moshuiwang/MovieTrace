"""Tests for movietrace.feedback.pull."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, call

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))


def _make_hot_record(
    record_id="rec1",
    title="Test Show",
    discovery_date_ms=None,
    content_update_id="discovery:tv:1234:2026-05-15",
    priority="P1",
    hot_score=80.0,
    tmdb_id="1234",
    operator_status="待看",
    operator_note="",
    vendor_status="未提交",
    assignee=None,
):
    from datetime import datetime
    from zoneinfo import ZoneInfo
    if discovery_date_ms is None:
        # 2026-05-15 in epoch ms (Asia/Shanghai)
        dt = datetime(2026, 5, 15, tzinfo=ZoneInfo("Asia/Shanghai"))
        discovery_date_ms = int(dt.timestamp() * 1000)
    # Feishu search API returns fields by Chinese name, not field ID
    return {
        "record_id": record_id,
        "fields": {
            "标题": [{"text": title, "type": "text"}],
            "发现日期": discovery_date_ms,
            "content_update_id": [{"text": content_update_id, "type": "text"}],
            "类型": "tv",
            "优先级": priority,
            "hot_score": hot_score,
            "TMDb ID": [{"text": tmdb_id, "type": "text"}],
            "运营状态": operator_status,
            "运营备注": [{"text": operator_note, "type": "text"}] if operator_note else [],
            "供应商状态": vendor_status,
            "负责人": [{"id": assignee}] if assignee else [],
        },
    }


def _make_gap_record(
    record_id="gap1",
    tmdb_id="5678",
    name="Gap Show",
    hot_score=60.0,
    gap_count=2,
    gap_seasons="S4,S5",
    operator_status="待补",
    operator_note="",
    assignee=None,
):
    return {
        "record_id": record_id,
        "fields": {
            "TMDb ID": [{"text": tmdb_id, "type": "text"}],
            "剧集名": [{"text": name, "type": "text"}],
            "hot_score": hot_score,
            "缺口数": gap_count,
            "缺口季": [{"text": gap_seasons, "type": "text"}],
            "运营状态": operator_status,
            "备注": [{"text": operator_note, "type": "text"}] if operator_note else [],
            "负责人": [{"id": assignee}] if assignee else [],
        },
    }


class TestPullHotTable(unittest.TestCase):
    def _fake_list_records(self, records):
        """Return a mock that yields records from a fake search response."""
        resp = {
            "code": 0,
            "data": {"items": records, "has_more": False},
        }
        return resp

    def test_pull_hot_table_filters_by_date(self):
        from movietrace.feedback.pull import pull_hot_table
        from datetime import datetime, timedelta
        from zoneinfo import ZoneInfo

        TZ = ZoneInfo("Asia/Shanghai")
        # Old record: 30 days ago
        old_ms = int((datetime.now(TZ) - timedelta(days=30)).timestamp() * 1000)
        # Recent record: today
        recent_ms = int(datetime.now(TZ).timestamp() * 1000)

        records = [
            _make_hot_record(record_id="old", discovery_date_ms=old_ms),
            _make_hot_record(record_id="new", discovery_date_ms=recent_ms),
        ]

        mock_resp = {
            "code": 0,
            "data": {"items": records, "has_more": False},
        }

        with patch("movietrace.feedback.pull._request_with_retry", return_value=mock_resp):
            result = pull_hot_table("tok", "app_token", "table_id", days=7)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["record_id"], "new")

    def test_pull_hot_table_extracts_fields(self):
        from movietrace.feedback.pull import pull_hot_table
        from datetime import datetime
        from zoneinfo import ZoneInfo

        TZ = ZoneInfo("Asia/Shanghai")
        today_ms = int(datetime.now(TZ).timestamp() * 1000)

        records = [_make_hot_record(
            record_id="r1",
            title="My Show",
            discovery_date_ms=today_ms,
            priority="P0",
            hot_score=95.0,
            tmdb_id="9999",
            operator_status="确认加入",
            operator_note="good pick",
            vendor_status="已提交",
        )]
        mock_resp = {"code": 0, "data": {"items": records, "has_more": False}}

        with patch("movietrace.feedback.pull._request_with_retry", return_value=mock_resp):
            result = pull_hot_table("tok", "app_token", "table_id", days=7)

        self.assertEqual(len(result), 1)
        r = result[0]
        self.assertEqual(r["title"], "My Show")
        self.assertEqual(r["priority"], "P0")
        self.assertEqual(r["hot_score"], 95.0)
        self.assertEqual(r["tmdb_id"], "9999")
        self.assertEqual(r["operator_status"], "确认加入")
        self.assertEqual(r["operator_note"], "good pick")
        self.assertEqual(r["vendor_status"], "已提交")

    def test_pull_hot_table_empty_table(self):
        from movietrace.feedback.pull import pull_hot_table
        mock_resp = {"code": 0, "data": {"items": [], "has_more": False}}

        with patch("movietrace.feedback.pull._request_with_retry", return_value=mock_resp):
            result = pull_hot_table("tok", "app_token", "table_id", days=7)

        self.assertEqual(result, [])

    def test_pull_hot_table_pagination(self):
        from movietrace.feedback.pull import pull_hot_table
        from datetime import datetime
        from zoneinfo import ZoneInfo

        TZ = ZoneInfo("Asia/Shanghai")
        today_ms = int(datetime.now(TZ).timestamp() * 1000)

        page1 = {"code": 0, "data": {"items": [_make_hot_record(record_id="r1", discovery_date_ms=today_ms)], "has_more": True, "page_token": "tok1"}}
        page2 = {"code": 0, "data": {"items": [_make_hot_record(record_id="r2", discovery_date_ms=today_ms)], "has_more": False}}

        with patch("movietrace.feedback.pull._request_with_retry", side_effect=[page1, page2]):
            result = pull_hot_table("tok", "app_token", "table_id", days=7)

        self.assertEqual(len(result), 2)


class TestPullGapTable(unittest.TestCase):
    def test_pull_gap_table_extracts_fields(self):
        from movietrace.feedback.pull import pull_gap_table

        records = [_make_gap_record(
            tmdb_id="5678",
            name="Gap Show",
            hot_score=75.0,
            gap_count=3,
            gap_seasons="S5,S6,S7",
            operator_status="已补",
            operator_note="完成了",
        )]
        mock_resp = {"code": 0, "data": {"items": records, "has_more": False}}

        with patch("movietrace.feedback.pull._request_with_retry", return_value=mock_resp):
            result = pull_gap_table("tok", "app_token", "table_id")

        self.assertEqual(len(result), 1)
        r = result[0]
        self.assertEqual(r["tmdb_id"], "5678")
        self.assertEqual(r["name"], "Gap Show")
        self.assertEqual(r["hot_score"], 75.0)
        self.assertEqual(r["gap_count"], 3)
        self.assertEqual(r["gap_seasons"], "S5,S6,S7")
        self.assertEqual(r["operator_status"], "已补")
        self.assertEqual(r["operator_note"], "完成了")

    def test_pull_gap_table_empty(self):
        from movietrace.feedback.pull import pull_gap_table
        mock_resp = {"code": 0, "data": {"items": [], "has_more": False}}

        with patch("movietrace.feedback.pull._request_with_retry", return_value=mock_resp):
            result = pull_gap_table("tok", "app_token", "table_id")

        self.assertEqual(result, [])


class TestRetry(unittest.TestCase):
    def test_retry_succeeds_on_third_attempt(self):
        from movietrace.feedback.pull import _request_with_retry

        ok_resp = {"code": 0, "data": {}}
        attempts = {"n": 0}

        def side_effect(*args, **kwargs):
            attempts["n"] += 1
            if attempts["n"] < 3:
                raise RuntimeError("transient error")
            return ok_resp

        with patch("movietrace.feedback.pull.request_json", side_effect=side_effect):
            with patch("movietrace.feedback.pull.time.sleep"):
                result = _request_with_retry("GET", "http://example.com", token="tok")

        self.assertEqual(result, ok_resp)
        self.assertEqual(attempts["n"], 3)

    def test_retry_raises_after_three_failures(self):
        from movietrace.feedback.pull import _request_with_retry

        with patch("movietrace.feedback.pull.request_json", side_effect=RuntimeError("always fails")):
            with patch("movietrace.feedback.pull.time.sleep"):
                with self.assertRaises(RuntimeError):
                    _request_with_retry("GET", "http://example.com", token="tok")


if __name__ == "__main__":
    unittest.main()
