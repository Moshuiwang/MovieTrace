"""Unit tests for pure functions in feishu/sync.py."""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pytest

from movietrace.feishu.sync import _to_epoch_ms, _derive_content_type

UTC = timezone.utc
CST = ZoneInfo("Asia/Shanghai")


class TestToEpochMs:
    def test_date_only_default_tz(self):
        result = _to_epoch_ms("2026-05-16")
        assert result is not None
        dt = datetime.fromtimestamp(result / 1000, CST)
        assert dt.year == 2026
        assert dt.month == 5
        assert dt.day == 16
        assert dt.hour == 0

    def test_datetime_default_tz(self):
        result = _to_epoch_ms("2026-05-16 10:30:45")
        assert result is not None
        dt = datetime.fromtimestamp(result / 1000, CST)
        assert dt.year == 2026
        assert dt.month == 5
        assert dt.day == 16
        assert dt.hour == 10
        assert dt.minute == 30
        assert dt.second == 45

    def test_datetime_utc_vs_cst_differs_by_8h(self):
        dt_str = "2026-05-16 10:30:45"
        result_cst = _to_epoch_ms(dt_str, tz=CST)
        result_utc = _to_epoch_ms(dt_str, tz=UTC)
        assert result_cst is not None
        assert result_utc is not None
        # CST is UTC+8, so parsing same wall-clock in CST gives earlier epoch
        assert result_utc - result_cst == 8 * 3600 * 1000

    def test_empty_string_returns_none(self):
        assert _to_epoch_ms("") is None

    def test_none_returns_none(self):
        assert _to_epoch_ms(None) is None  # type: ignore[arg-type]

    def test_invalid_format_returns_none(self):
        assert _to_epoch_ms("not-a-date") is None


class TestDeriveContentType:
    def test_content_type_field_short_circuits(self):
        assert _derive_content_type({"content_type": "movie"}) == "movie"

    def test_new_season_update_type_returns_tv(self):
        assert _derive_content_type({"update_type": "new_season"}) == "tv"

    def test_discovery_movie_id(self):
        rec = {"content_update_id": "discovery:movie:12345:2026-05-16"}
        assert _derive_content_type(rec) == "movie"

    def test_discovery_tv_id(self):
        rec = {"content_update_id": "discovery:tv:67890:2026-05-16"}
        assert _derive_content_type(rec) == "tv"

    def test_empty_record_returns_unknown(self):
        assert _derive_content_type({}) == "unknown"
