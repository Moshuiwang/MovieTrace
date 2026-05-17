"""Tests for feishu/sync.py P1.24 field mapping extensions."""

import json
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import tempfile

from movietrace.feishu.sync import (
    _build_imdb_url,
    _build_tmdb_url,
    sync_table,
)


class TestBuildImdbUrl:
    """Tests for _build_imdb_url helper."""

    def test_build_imdb_url_empty_string(self):
        """Empty string -> empty string."""
        result = _build_imdb_url("")
        assert result == ""

    def test_build_imdb_url_none(self):
        """None -> empty string."""
        result = _build_imdb_url(None)
        assert result == ""

    def test_build_imdb_url_whitespace(self):
        """Whitespace-only -> empty string."""
        result = _build_imdb_url("   ")
        assert result == ""

    def test_build_imdb_url_valid_id(self):
        """Valid IMDb ID -> Feishu URL field format."""
        result = _build_imdb_url("tt0903747")
        assert isinstance(result, dict)
        assert result["link"] == "https://www.imdb.com/title/tt0903747/"
        assert result["text"] == "tt0903747"

    def test_build_imdb_url_with_leading_whitespace(self):
        """IMDb ID with leading/trailing whitespace -> stripped."""
        result = _build_imdb_url("  tt1234567  ")
        assert result["link"] == "https://www.imdb.com/title/tt1234567/"
        assert result["text"] == "tt1234567"


class TestBuildTmdbUrl:
    """Tests for _build_tmdb_url helper."""

    def test_build_tmdb_url_empty(self):
        """Empty tmdb_id -> empty string."""
        result = _build_tmdb_url("", "tv")
        assert result == ""

    def test_build_tmdb_url_none(self):
        """None tmdb_id -> empty string."""
        result = _build_tmdb_url(None, "movie")
        assert result == ""

    def test_build_tmdb_url_tv(self):
        """TV type tmdb_id -> /tv/ path."""
        result = _build_tmdb_url("1396", "tv")
        assert isinstance(result, dict)
        assert result["link"] == "https://www.themoviedb.org/tv/1396"
        assert result["text"] == "1396"

    def test_build_tmdb_url_show_alias(self):
        """'show' content type -> /tv/ path (same as tv)."""
        result = _build_tmdb_url("550", "show")
        assert result["link"] == "https://www.themoviedb.org/tv/550"

    def test_build_tmdb_url_movie(self):
        """Movie type tmdb_id -> /movie/ path."""
        result = _build_tmdb_url("550", "movie")
        assert isinstance(result, dict)
        assert result["link"] == "https://www.themoviedb.org/movie/550"
        assert result["text"] == "550"

    def test_build_tmdb_url_unknown_type_defaults_to_movie(self):
        """Unknown content type -> defaults to /movie/."""
        result = _build_tmdb_url("999", "unknown")
        assert result["link"] == "https://www.themoviedb.org/movie/999"

    def test_build_tmdb_url_with_whitespace(self):
        """tmdb_id with whitespace -> stripped."""
        result = _build_tmdb_url("  123  ", "tv")
        assert result["link"] == "https://www.themoviedb.org/tv/123"


class TestSyncTableFieldsExtension:
    """Tests for P1.24 field extensions in sync_table."""

    def _make_test_record(self, **overrides) -> dict:
        """Create a minimal test record with P1.24 fields."""
        base_source_summary = {
            "imdb_id": "tt0903747",
            "last_episode_to_air": {"season_number": 22, "episode_number": 18, "air_date": "2024-05-18"},
            "genres": [10766],  # Soap
            "score_breakdown": {
                "flixpatrol_score": 45.5,
                "imdb_rating_score": 87.2,
                "tmdb_rating_score": 79.5,
                "tmdb_popularity_score": 92.1,
                "trakt_score": 81.0,
            },
            "row_duration_hours": 3.5,
            "ops_note": "TMDb 标识为 Soap,自动降权",
            "is_soap": True,
        }
        source_summary = overrides.pop("source_summary", base_source_summary)

        base = {
            "content_update_id": "discovery:tv:1396:2026-05-17",
            "update_type": "new_discovery",
            "priority": "P2",
            "hot_score": 75.0,
            "title": "Grey's Anatomy",
            "tmdb_id": "1396",
            "tmdb_tv_id": None,
            "upstream_max_season": 21,
            "match_confidence_low": False,
            "source_data_status": {},
            "event_written_at_utc": "2026-05-17 10:30:00",
            "created_at": "2026-05-17 10:30:00",
            "season": 22,
            "source_summary_json": json.dumps(source_summary, ensure_ascii=False),
        }
        base.update(overrides)
        return base

    @patch("movietrace.feishu.sync.fetch_tenant_access_token")
    @patch("movietrace.feishu.sync.ensure_table_fields")
    @patch("movietrace.feishu.sync._list_records_for_date")
    @patch("movietrace.feishu.sync.batch_create_records")
    @patch("movietrace.feishu.sync.batch_update_records")
    def test_sync_table_extends_fields_with_p1_24(
        self,
        mock_batch_update,
        mock_batch_create,
        mock_list_records,
        mock_ensure_fields,
        mock_fetch_token,
    ):
        """sync_table includes P1.24 new fields in create records."""
        mock_fetch_token.return_value = "token"
        mock_ensure_fields.return_value = {
            "created": [],
            "existed": [],
            "renamed": [],
            "errors": [],
            "dry_run": False,
        }
        mock_list_records.return_value = {}

        # Create test JSON
        record = self._make_test_record()
        json_content = json.dumps([record], ensure_ascii=False)

        with tempfile.TemporaryDirectory() as tmpdir:
            json_path = Path(tmpdir) / "latest.json"
            json_path.write_text(json_content, encoding="utf-8")

            result = sync_table(
                json_path=str(json_path),
                run_date="2026-05-17",
                app_id="test_app",
                app_secret="test_secret",
                app_token="test_token",
                table_id="test_table",
            )

        # Verify sync_table was called and fields were created
        assert result["created"] == 1
        assert result["updated"] == 0

        # Verify batch_create_records was called with correct fields
        mock_batch_create.assert_called_once()
        call_args = mock_batch_create.call_args
        batch_records = call_args[0][3]  # 4th arg is the records list
        assert len(batch_records) == 1

        fields = batch_records[0]["fields"]
        assert "在播最新季" in fields
        assert fields["在播最新季"] == 22
        assert "预估时长" in fields
        assert fields["预估时长"] == 3.5
        assert "FP 热度分" in fields
        assert fields["FP 热度分"] == 45.5
        assert "IMDb 评分" in fields
        assert fields["IMDb 评分"] == 87.2
        assert "TMDb 评分" in fields
        assert fields["TMDb 评分"] == 79.5
        assert "TMDb 热度分" in fields
        assert fields["TMDb 热度分"] == 92.1
        assert "Trakt 热度分" in fields
        assert fields["Trakt 热度分"] == 81.0
        assert "IMDb 链接" in fields
        assert "TMDb 链接" in fields

    @patch("movietrace.feishu.sync.fetch_tenant_access_token")
    @patch("movietrace.feishu.sync.ensure_table_fields")
    @patch("movietrace.feishu.sync._list_records_for_date")
    @patch("movietrace.feishu.sync.batch_create_records")
    @patch("movietrace.feishu.sync.batch_update_records")
    def test_sync_table_create_includes_ops_note_for_soap(
        self,
        mock_batch_update,
        mock_batch_create,
        mock_list_records,
        mock_ensure_fields,
        mock_fetch_token,
    ):
        """Create path includes ops_note field when present."""
        mock_fetch_token.return_value = "token"
        mock_ensure_fields.return_value = {
            "created": [],
            "existed": [],
            "renamed": [],
            "errors": [],
            "dry_run": False,
        }
        mock_list_records.return_value = {}

        source_summary = {
            "imdb_id": "tt1234567",
            "last_episode_to_air": {"season_number": 5},
            "score_breakdown": {},
            "row_duration_hours": 1.5,
            "ops_note": "TMDb 标识为 Soap,自动降权",
            "is_soap": True,
        }
        record = self._make_test_record(source_summary=source_summary)
        json_content = json.dumps([record], ensure_ascii=False)

        with tempfile.TemporaryDirectory() as tmpdir:
            json_path = Path(tmpdir) / "latest.json"
            json_path.write_text(json_content, encoding="utf-8")

            sync_table(
                json_path=str(json_path),
                run_date="2026-05-17",
                app_id="test_app",
                app_secret="test_secret",
                app_token="test_token",
                table_id="test_table",
            )

        # Verify ops_note is in create fields
        mock_batch_create.assert_called_once()
        batch_records = mock_batch_create.call_args[0][3]
        fields = batch_records[0]["fields"]
        assert "运营备注" in fields
        assert fields["运营备注"] == "TMDb 标识为 Soap,自动降权"

    @patch("movietrace.feishu.sync.fetch_tenant_access_token")
    @patch("movietrace.feishu.sync.ensure_table_fields")
    @patch("movietrace.feishu.sync._list_records_for_date")
    @patch("movietrace.feishu.sync.batch_create_records")
    @patch("movietrace.feishu.sync.batch_update_records")
    def test_sync_table_update_excludes_ops_note(
        self,
        mock_batch_update,
        mock_batch_create,
        mock_list_records,
        mock_ensure_fields,
        mock_fetch_token,
    ):
        """Update path does NOT include ops_note (protects human edits)."""
        mock_fetch_token.return_value = "token"
        mock_ensure_fields.return_value = {
            "created": [],
            "existed": [],
            "renamed": [],
            "errors": [],
            "dry_run": False,
        }
        # Record already exists
        mock_list_records.return_value = {
            "2026-05-17|discovery:tv:1396:2026-05-17": "record_id_123"
        }

        source_summary = {
            "imdb_id": "tt1234567",
            "last_episode_to_air": {"season_number": 5},
            "score_breakdown": {},
            "row_duration_hours": 1.5,
            "ops_note": "TMDb 标识为 Soap,自动降权",
            "is_soap": True,
        }
        record = self._make_test_record(source_summary=source_summary)
        json_content = json.dumps([record], ensure_ascii=False)

        with tempfile.TemporaryDirectory() as tmpdir:
            json_path = Path(tmpdir) / "latest.json"
            json_path.write_text(json_content, encoding="utf-8")

            sync_table(
                json_path=str(json_path),
                run_date="2026-05-17",
                app_id="test_app",
                app_secret="test_secret",
                app_token="test_token",
                table_id="test_table",
            )

        # Verify ops_note is NOT in update fields
        mock_batch_update.assert_called_once()
        updates = mock_batch_update.call_args[0][3]
        fields = updates[0]["fields"]
        assert "运营备注" not in fields

    @patch("movietrace.feishu.sync.fetch_tenant_access_token")
    @patch("movietrace.feishu.sync.ensure_table_fields")
    @patch("movietrace.feishu.sync._list_records_for_date")
    @patch("movietrace.feishu.sync.batch_create_records")
    @patch("movietrace.feishu.sync.batch_update_records")
    def test_sync_table_no_legacy_season_field(
        self,
        mock_batch_update,
        mock_batch_create,
        mock_list_records,
        mock_ensure_fields,
        mock_fetch_token,
    ):
        """Legacy '季号' field is not present in any output."""
        mock_fetch_token.return_value = "token"
        mock_ensure_fields.return_value = {
            "created": [],
            "existed": [],
            "renamed": [],
            "errors": [],
            "dry_run": False,
        }
        mock_list_records.return_value = {}

        record = self._make_test_record()
        json_content = json.dumps([record], ensure_ascii=False)

        with tempfile.TemporaryDirectory() as tmpdir:
            json_path = Path(tmpdir) / "latest.json"
            json_path.write_text(json_content, encoding="utf-8")

            sync_table(
                json_path=str(json_path),
                run_date="2026-05-17",
                app_id="test_app",
                app_secret="test_secret",
                app_token="test_token",
                table_id="test_table",
            )

        mock_batch_create.assert_called_once()
        batch_records = mock_batch_create.call_args[0][3]
        fields = batch_records[0]["fields"]
        # Legacy "季号" should NOT be present
        assert "季号" not in fields
        # New "在播最新季" should be present
        assert "在播最新季" in fields

    @patch("movietrace.feishu.sync.fetch_tenant_access_token")
    @patch("movietrace.feishu.sync.ensure_table_fields")
    @patch("movietrace.feishu.sync._list_records_for_date")
    @patch("movietrace.feishu.sync.batch_create_records")
    @patch("movietrace.feishu.sync.batch_update_records")
    def test_sync_table_calls_ensure_fields(
        self,
        mock_batch_update,
        mock_batch_create,
        mock_list_records,
        mock_ensure_fields,
        mock_fetch_token,
    ):
        """sync_table calls ensure_table_fields once at start."""
        mock_fetch_token.return_value = "token"
        mock_ensure_fields.return_value = {
            "created": [{"field_name": "在播最新季"}],
            "existed": [],
            "renamed": [{"old_name": "季号", "new_name": "在播最新季"}],
            "errors": [],
            "dry_run": False,
        }
        mock_list_records.return_value = {}

        record = self._make_test_record()
        json_content = json.dumps([record], ensure_ascii=False)

        with tempfile.TemporaryDirectory() as tmpdir:
            json_path = Path(tmpdir) / "latest.json"
            json_path.write_text(json_content, encoding="utf-8")

            sync_table(
                json_path=str(json_path),
                run_date="2026-05-17",
                app_id="test_app",
                app_secret="test_secret",
                app_token="test_token",
                table_id="test_table",
            )

        # Verify ensure_table_fields was called exactly once with correct params
        mock_ensure_fields.assert_called_once()
        call_kwargs = mock_ensure_fields.call_args[1]
        assert call_kwargs["app_id"] == "test_app"
        assert call_kwargs["app_secret"] == "test_secret"
        assert call_kwargs["app_token"] == "test_token"
        assert call_kwargs["table_id"] == "test_table"
        assert call_kwargs["dry_run"] is False

    @patch("movietrace.feishu.sync.fetch_tenant_access_token")
    @patch("movietrace.feishu.sync.ensure_table_fields")
    @patch("movietrace.feishu.sync._list_records_for_date")
    @patch("movietrace.feishu.sync.batch_create_records")
    @patch("movietrace.feishu.sync.batch_update_records")
    def test_sync_table_handles_missing_source_summary(
        self,
        mock_batch_update,
        mock_batch_create,
        mock_list_records,
        mock_ensure_fields,
        mock_fetch_token,
    ):
        """Missing source_summary_json -> fields still created with defaults."""
        mock_fetch_token.return_value = "token"
        mock_ensure_fields.return_value = {
            "created": [],
            "existed": [],
            "renamed": [],
            "errors": [],
            "dry_run": False,
        }
        mock_list_records.return_value = {}

        # Record without source_summary_json (legacy compatibility)
        record = self._make_test_record(source_summary_json="")
        json_content = json.dumps([record], ensure_ascii=False)

        with tempfile.TemporaryDirectory() as tmpdir:
            json_path = Path(tmpdir) / "latest.json"
            json_path.write_text(json_content, encoding="utf-8")

            result = sync_table(
                json_path=str(json_path),
                run_date="2026-05-17",
                app_id="test_app",
                app_secret="test_secret",
                app_token="test_token",
                table_id="test_table",
            )

        # Should not crash; should create record with defaults
        assert result["created"] == 1
        assert result["errors"] == 0

    @patch("movietrace.feishu.sync.fetch_tenant_access_token")
    @patch("movietrace.feishu.sync.ensure_table_fields")
    @patch("movietrace.feishu.sync._list_records_for_date")
    @patch("movietrace.feishu.sync.batch_create_records")
    @patch("movietrace.feishu.sync.batch_update_records")
    def test_sync_table_movie_has_no_last_aired_season(
        self,
        mock_batch_update,
        mock_batch_create,
        mock_list_records,
        mock_ensure_fields,
        mock_fetch_token,
    ):
        """Movie records should not have 在播最新季 (no last_episode_to_air)."""
        mock_fetch_token.return_value = "token"
        mock_ensure_fields.return_value = {
            "created": [],
            "existed": [],
            "renamed": [],
            "errors": [],
            "dry_run": False,
        }
        mock_list_records.return_value = {}

        source_summary = {
            "imdb_id": "tt0111161",
            "last_episode_to_air": None,  # Movies don't have this
            "score_breakdown": {"imdb_rating_score": 95.5},
            "row_duration_hours": 2.0,
        }
        record = self._make_test_record(
            content_update_id="discovery:movie:278:2026-05-17",
            update_type="new_discovery",
            tmdb_id="278",
            season=None,
            source_summary=source_summary,
        )
        json_content = json.dumps([record], ensure_ascii=False)

        with tempfile.TemporaryDirectory() as tmpdir:
            json_path = Path(tmpdir) / "latest.json"
            json_path.write_text(json_content, encoding="utf-8")

            sync_table(
                json_path=str(json_path),
                run_date="2026-05-17",
                app_id="test_app",
                app_secret="test_secret",
                app_token="test_token",
                table_id="test_table",
            )

        mock_batch_create.assert_called_once()
        batch_records = mock_batch_create.call_args[0][3]
        fields = batch_records[0]["fields"]
        # Movie should not have 在播最新季 (or it should be None/missing)
        assert fields.get("在播最新季") is None or "在播最新季" not in fields
