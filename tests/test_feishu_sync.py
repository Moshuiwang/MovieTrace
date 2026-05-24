"""Tests for feishu/sync.py P1.24 field mapping extensions."""

import json
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import tempfile

from movietrace.feishu.sync import (
    _build_imdb_url,
    _build_tmdb_url,
    _compute_type_labels,
    _list_discovery_records_by_keys,
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

    def test_build_imdb_url_bare_numeric_7_digit(self):
        """Bare 7-digit numeric ID gets tt prefix (issue #7 regression)."""
        result = _build_imdb_url("1190634")
        assert result["link"] == "https://www.imdb.com/title/tt1190634/"
        assert result["text"] == "tt1190634"

    def test_build_imdb_url_bare_numeric_8_digit(self):
        """Bare 8-digit numeric ID is not truncated by zfill(7)."""
        result = _build_imdb_url("31589662")
        assert result["link"] == "https://www.imdb.com/title/tt31589662/"
        assert result["text"] == "tt31589662"

    def test_build_imdb_url_short_numeric_padded(self):
        """Short numeric ID is zero-padded to 7 digits per IMDb canonical form."""
        result = _build_imdb_url("123")
        assert result["link"] == "https://www.imdb.com/title/tt0000123/"
        assert result["text"] == "tt0000123"

    def test_build_imdb_url_idempotent_tt_prefix(self):
        """Already tt-prefixed ID is not re-prefixed."""
        result = _build_imdb_url("tt1190634")
        assert result["link"] == "https://www.imdb.com/title/tt1190634/"
        assert result["text"] == "tt1190634"


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
            "imdb": {"rating": "8.3", "votes": "1,234,567"},
            "tmdb": {"vote_average": 7.9, "vote_count": 12345},
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
            "content_update_id": "discovery:tv:1396",
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
    @patch("movietrace.feishu.sync._list_discovery_records_by_keys")
    @patch("movietrace.feishu.sync.batch_create_records")
    @patch("movietrace.feishu.sync.batch_update_records")
    def test_sync_table_extends_fields_with_p1_24(
        self,
        mock_batch_update,
        mock_batch_create,
        mock_list_discovery,
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
        mock_list_discovery.return_value = {}

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
        assert fields["IMDb 评分"] == 8.3
        assert "TMDb 评分" in fields
        assert fields["TMDb 评分"] == 7.9
        assert "TMDb 热度分" in fields
        assert fields["TMDb 热度分"] == 92.1
        assert "Trakt 热度分" in fields
        assert fields["Trakt 热度分"] == 81.0
        assert "IMDb 链接" in fields
        assert "TMDb 链接" in fields

    @patch("movietrace.feishu.sync.fetch_tenant_access_token")
    @patch("movietrace.feishu.sync.ensure_table_fields")
    @patch("movietrace.feishu.sync._list_records_for_date")
    @patch("movietrace.feishu.sync._list_discovery_records_by_keys")
    @patch("movietrace.feishu.sync.batch_create_records")
    @patch("movietrace.feishu.sync.batch_update_records")
    def test_sync_table_create_includes_ops_note_for_soap(
        self,
        mock_batch_update,
        mock_batch_create,
        mock_list_discovery,
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
        mock_list_discovery.return_value = {}

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
    @patch("movietrace.feishu.sync._list_discovery_records_by_keys")
    @patch("movietrace.feishu.sync.batch_create_records")
    @patch("movietrace.feishu.sync.batch_update_records")
    def test_sync_table_update_excludes_ops_note(
        self,
        mock_batch_update,
        mock_batch_create,
        mock_list_discovery,
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
        # new_season lookup (not used for this record, but must not raise)
        mock_list_records.return_value = {}
        # discovery stable key lookup: record already exists (D2: use stable key without date)
        mock_list_discovery.return_value = {
            "discovery:tv:1396": "record_id_123"
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
        # Also verify other ops fields are excluded
        assert "运营状态" not in fields
        assert "供应商状态" not in fields

    @patch("movietrace.feishu.sync.fetch_tenant_access_token")
    @patch("movietrace.feishu.sync.ensure_table_fields")
    @patch("movietrace.feishu.sync._list_records_for_date")
    @patch("movietrace.feishu.sync._list_discovery_records_by_keys")
    @patch("movietrace.feishu.sync.batch_create_records")
    @patch("movietrace.feishu.sync.batch_update_records")
    def test_sync_table_no_legacy_season_field(
        self,
        mock_batch_update,
        mock_batch_create,
        mock_list_discovery,
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
        mock_list_discovery.return_value = {}

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
    @patch("movietrace.feishu.sync._list_discovery_records_by_keys")
    @patch("movietrace.feishu.sync.batch_create_records")
    @patch("movietrace.feishu.sync.batch_update_records")
    def test_sync_table_calls_ensure_fields(
        self,
        mock_batch_update,
        mock_batch_create,
        mock_list_discovery,
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
        mock_list_discovery.return_value = {}

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
    @patch("movietrace.feishu.sync._list_discovery_records_by_keys")
    @patch("movietrace.feishu.sync.batch_create_records")
    @patch("movietrace.feishu.sync.batch_update_records")
    def test_sync_table_handles_missing_source_summary(
        self,
        mock_batch_update,
        mock_batch_create,
        mock_list_discovery,
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
        mock_list_discovery.return_value = {}

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
    @patch("movietrace.feishu.sync._list_discovery_records_by_keys")
    @patch("movietrace.feishu.sync.batch_create_records")
    @patch("movietrace.feishu.sync.batch_update_records")
    def test_sync_table_movie_has_no_last_aired_season(
        self,
        mock_batch_update,
        mock_batch_create,
        mock_list_discovery,
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
        mock_list_discovery.return_value = {}

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

    @patch("movietrace.feishu.sync.fetch_tenant_access_token")
    @patch("movietrace.feishu.sync.ensure_table_fields")
    @patch("movietrace.feishu.sync._list_records_for_date")
    @patch("movietrace.feishu.sync._list_discovery_records_by_keys")
    @patch("movietrace.feishu.sync.batch_create_records")
    @patch("movietrace.feishu.sync.batch_update_records")
    def test_a_ku_max_season_written_as_integer(
        self,
        mock_batch_update,
        mock_batch_create,
        mock_list_discovery,
        mock_list_records,
        mock_ensure_fields,
        mock_fetch_token,
    ):
        """A库最新季 is written as integer, not string 'S3'."""
        mock_fetch_token.return_value = "token"
        mock_ensure_fields.return_value = {"created": [], "existed": [], "renamed": [], "errors": [], "dry_run": False}
        mock_list_records.return_value = {}
        mock_list_discovery.return_value = {}

        record = self._make_test_record(upstream_max_season=3)
        json_content = json.dumps([record], ensure_ascii=False)

        with tempfile.TemporaryDirectory() as tmpdir:
            json_path = Path(tmpdir) / "latest.json"
            json_path.write_text(json_content, encoding="utf-8")
            sync_table(json_path=str(json_path), run_date="2026-05-17",
                       app_id="a", app_secret="s", app_token="t", table_id="tbl")

        fields = mock_batch_create.call_args[0][3][0]["fields"]
        assert fields["A库最新季"] == 3
        assert not isinstance(fields["A库最新季"], str)

    @patch("movietrace.feishu.sync.fetch_tenant_access_token")
    @patch("movietrace.feishu.sync.ensure_table_fields")
    @patch("movietrace.feishu.sync._list_records_for_date")
    @patch("movietrace.feishu.sync._list_discovery_records_by_keys")
    @patch("movietrace.feishu.sync.batch_create_records")
    @patch("movietrace.feishu.sync.batch_update_records")
    def test_a_ku_max_season_none_when_no_upstream(
        self,
        mock_batch_update,
        mock_batch_create,
        mock_list_discovery,
        mock_list_records,
        mock_ensure_fields,
        mock_fetch_token,
    ):
        """A库最新季 is absent from fields when upstream_max_season is None."""
        mock_fetch_token.return_value = "token"
        mock_ensure_fields.return_value = {"created": [], "existed": [], "renamed": [], "errors": [], "dry_run": False}
        mock_list_records.return_value = {}
        mock_list_discovery.return_value = {}

        record = self._make_test_record(upstream_max_season=None)
        json_content = json.dumps([record], ensure_ascii=False)

        with tempfile.TemporaryDirectory() as tmpdir:
            json_path = Path(tmpdir) / "latest.json"
            json_path.write_text(json_content, encoding="utf-8")
            sync_table(json_path=str(json_path), run_date="2026-05-17",
                       app_id="a", app_secret="s", app_token="t", table_id="tbl")

        fields = mock_batch_create.call_args[0][3][0]["fields"]
        assert "A库最新季" not in fields

    @patch("movietrace.feishu.sync.fetch_tenant_access_token")
    @patch("movietrace.feishu.sync.ensure_table_fields")
    @patch("movietrace.feishu.sync._list_records_for_date")
    @patch("movietrace.feishu.sync._list_discovery_records_by_keys")
    @patch("movietrace.feishu.sync.batch_create_records")
    @patch("movietrace.feishu.sync.batch_update_records")
    def test_episode_count_fields_written_when_present(
        self,
        mock_batch_update,
        mock_batch_create,
        mock_list_discovery,
        mock_list_records,
        mock_ensure_fields,
        mock_fetch_token,
    ):
        """A库总集数 and TMDB总集数 are written when the record has them."""
        mock_fetch_token.return_value = "token"
        mock_ensure_fields.return_value = {"created": [], "existed": [], "renamed": [], "errors": [], "dry_run": False}
        mock_list_records.return_value = {}
        mock_list_discovery.return_value = {}

        record = self._make_test_record(upstream_total_eps=50, tmdb_total_episodes=48)
        json_content = json.dumps([record], ensure_ascii=False)

        with tempfile.TemporaryDirectory() as tmpdir:
            json_path = Path(tmpdir) / "latest.json"
            json_path.write_text(json_content, encoding="utf-8")
            sync_table(json_path=str(json_path), run_date="2026-05-17",
                       app_id="a", app_secret="s", app_token="t", table_id="tbl")

        fields = mock_batch_create.call_args[0][3][0]["fields"]
        assert fields["A库总集数"] == 50
        assert fields["TMDB总集数"] == 48

    @patch("movietrace.feishu.sync.fetch_tenant_access_token")
    @patch("movietrace.feishu.sync.ensure_table_fields")
    @patch("movietrace.feishu.sync._list_records_for_date")
    @patch("movietrace.feishu.sync._list_discovery_records_by_keys")
    @patch("movietrace.feishu.sync.batch_create_records")
    @patch("movietrace.feishu.sync.batch_update_records")
    def test_episode_count_fields_absent_when_none(
        self,
        mock_batch_update,
        mock_batch_create,
        mock_list_discovery,
        mock_list_records,
        mock_ensure_fields,
        mock_fetch_token,
    ):
        """A库总集数 and TMDB总集数 are not written when the record lacks them."""
        mock_fetch_token.return_value = "token"
        mock_ensure_fields.return_value = {"created": [], "existed": [], "renamed": [], "errors": [], "dry_run": False}
        mock_list_records.return_value = {}
        mock_list_discovery.return_value = {}

        record = self._make_test_record()  # no upstream_total_eps / tmdb_total_episodes
        json_content = json.dumps([record], ensure_ascii=False)

        with tempfile.TemporaryDirectory() as tmpdir:
            json_path = Path(tmpdir) / "latest.json"
            json_path.write_text(json_content, encoding="utf-8")
            sync_table(json_path=str(json_path), run_date="2026-05-17",
                       app_id="a", app_secret="s", app_token="t", table_id="tbl")

        fields = mock_batch_create.call_args[0][3][0]["fields"]
        assert "A库总集数" not in fields
        assert "TMDB总集数" not in fields


class TestRatingHelpers:
    def test_to_float_rating_string(self):
        from movietrace.feishu.sync import _to_float_rating
        assert _to_float_rating("8.3") == 8.3

    def test_to_float_rating_none(self):
        from movietrace.feishu.sync import _to_float_rating
        assert _to_float_rating(None) is None

    def test_to_float_rating_empty(self):
        from movietrace.feishu.sync import _to_float_rating
        assert _to_float_rating("") is None

    def test_to_float_rating_na(self):
        from movietrace.feishu.sync import _to_float_rating
        assert _to_float_rating("N/A") is None

    def test_parse_votes_with_commas(self):
        from movietrace.feishu.sync import _parse_votes
        assert _parse_votes("1,234,567") == 1234567

    def test_parse_votes_none(self):
        from movietrace.feishu.sync import _parse_votes
        assert _parse_votes(None) is None

    def test_parse_votes_na_string(self):
        from movietrace.feishu.sync import _parse_votes
        assert _parse_votes("N/A") is None


class TestSyncTableEnsureNotification:
    """P1.30: sync_table 字段自动 ensure 后的 IM 通知行为。"""

    def _make_minimal_record(self) -> dict:
        return {
            "content_update_id": "discovery:tv:1396:2026-05-17",
            "update_type": "new_discovery",
            "priority": "P2",
            "hot_score": 50.0,
            "title": "Test",
            "tmdb_id": "1396",
            "source_data_status": {},
            "event_written_at_utc": "2026-05-17 10:30:00",
            "created_at": "2026-05-17 10:30:00",
            "source_summary_json": json.dumps({"score_breakdown": {}}, ensure_ascii=False),
        }

    @patch("movietrace.feishu.sync.send_text")
    @patch("movietrace.feishu.sync.send_alert")
    @patch("movietrace.feishu.sync.fetch_tenant_access_token")
    @patch("movietrace.feishu.sync.ensure_table_fields")
    @patch("movietrace.feishu.sync._list_records_for_date")
    @patch("movietrace.feishu.sync._list_discovery_records_by_keys")
    @patch("movietrace.feishu.sync.batch_create_records")
    @patch("movietrace.feishu.sync.batch_update_records")
    def test_notifies_when_fields_created(
        self, mock_update, mock_create, mock_list_discovery, mock_list, mock_ensure,
        mock_token, mock_alert, mock_text,
    ):
        mock_token.return_value = "tok"
        mock_ensure.return_value = {
            "created": [{"field_name": "中文名", "field_type": 1}],
            "existed": [], "renamed": [], "errors": [], "dry_run": False,
        }
        mock_list.return_value = {}
        mock_list_discovery.return_value = {}

        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir) / "latest.json"
            p.write_text(json.dumps([self._make_minimal_record()], ensure_ascii=False))
            sync_table(
                json_path=str(p), run_date="2026-05-17",
                app_id="a", app_secret="s", app_token="t", table_id="tbl",
                notify_chat_id="chat_xyz",
            )

        mock_text.assert_called_once()
        args, kwargs = mock_text.call_args
        assert args[0] == "chat_xyz"
        assert "中文名" in args[1]
        assert kwargs["receive_id_type"] == "chat_id"
        mock_alert.assert_not_called()

    @patch("movietrace.feishu.sync.send_text")
    @patch("movietrace.feishu.sync.send_alert")
    @patch("movietrace.feishu.sync.fetch_tenant_access_token")
    @patch("movietrace.feishu.sync.ensure_table_fields")
    @patch("movietrace.feishu.sync._list_records_for_date")
    @patch("movietrace.feishu.sync._list_discovery_records_by_keys")
    @patch("movietrace.feishu.sync.batch_create_records")
    @patch("movietrace.feishu.sync.batch_update_records")
    def test_no_notify_when_no_field_changes(
        self, mock_update, mock_create, mock_list_discovery, mock_list, mock_ensure,
        mock_token, mock_alert, mock_text,
    ):
        mock_token.return_value = "tok"
        mock_ensure.return_value = {
            "created": [], "existed": [{"field_name": "x"}], "renamed": [],
            "errors": [], "dry_run": False,
        }
        mock_list.return_value = {}
        mock_list_discovery.return_value = {}

        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir) / "latest.json"
            p.write_text(json.dumps([self._make_minimal_record()], ensure_ascii=False))
            sync_table(
                json_path=str(p), run_date="2026-05-17",
                app_id="a", app_secret="s", app_token="t", table_id="tbl",
                notify_chat_id="chat_xyz",
            )

        mock_text.assert_not_called()
        mock_alert.assert_not_called()

    @patch("movietrace.feishu.sync.send_text")
    @patch("movietrace.feishu.sync.send_alert")
    @patch("movietrace.feishu.sync.fetch_tenant_access_token")
    @patch("movietrace.feishu.sync.ensure_table_fields")
    def test_raises_and_alerts_when_ensure_fails(
        self, mock_ensure, mock_token, mock_alert, mock_text,
    ):
        mock_token.return_value = "tok"
        mock_ensure.side_effect = RuntimeError("Feishu create field failed (code=99991663): permission denied")

        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir) / "latest.json"
            p.write_text(json.dumps([self._make_minimal_record()], ensure_ascii=False))
            with pytest.raises(RuntimeError, match="permission denied"):
                sync_table(
                    json_path=str(p), run_date="2026-05-17",
                    app_id="a", app_secret="s", app_token="t", table_id="tbl",
                    notify_chat_id="chat_xyz",
                )

        mock_alert.assert_called_once()
        args, kwargs = mock_alert.call_args
        assert args[0] == "chat_xyz"
        assert args[1] == "error"
        assert "permission denied" in kwargs.get("detail", "")
        mock_text.assert_not_called()

    @patch("movietrace.feishu.sync.send_text")
    @patch("movietrace.feishu.sync.send_alert")
    @patch("movietrace.feishu.sync.fetch_tenant_access_token")
    @patch("movietrace.feishu.sync.ensure_table_fields")
    @patch("movietrace.feishu.sync._list_records_for_date")
    @patch("movietrace.feishu.sync._list_discovery_records_by_keys")
    @patch("movietrace.feishu.sync.batch_create_records")
    @patch("movietrace.feishu.sync.batch_update_records")
    def test_no_notify_when_chat_id_empty(
        self, mock_update, mock_create, mock_list_discovery, mock_list, mock_ensure,
        mock_token, mock_alert, mock_text,
    ):
        mock_token.return_value = "tok"
        mock_ensure.return_value = {
            "created": [{"field_name": "x", "field_type": 1}],
            "existed": [], "renamed": [], "errors": [], "dry_run": False,
        }
        mock_list.return_value = {}
        mock_list_discovery.return_value = {}

        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir) / "latest.json"
            p.write_text(json.dumps([self._make_minimal_record()], ensure_ascii=False))
            sync_table(
                json_path=str(p), run_date="2026-05-17",
                app_id="a", app_secret="s", app_token="t", table_id="tbl",
                # notify_chat_id 不传 → 默认空串
            )

        mock_text.assert_not_called()
        mock_alert.assert_not_called()


class TestComputeTypeLabels:
    """P1.41: _compute_type_labels() unit tests."""

    def test_compute_type_labels_movie(self):
        rec = {"content_type": "movie", "genres_json": '[{"id":28,"name":"Action"}]'}
        assert _compute_type_labels(rec) == ["Action"]

    def test_compute_type_labels_tv_multi_genre(self):
        rec = {
            "content_type": "tv",
            "genres_json": '[{"id":18,"name":"Drama"},{"id":878,"name":"Science Fiction"}]',
        }
        assert _compute_type_labels(rec) == ["Drama", "Science Fiction"]

    def test_compute_type_labels_no_genres(self):
        rec = {"content_type": "tv", "genres_json": None}
        assert _compute_type_labels(rec) == []

    def test_compute_type_labels_empty_rec(self):
        assert _compute_type_labels({}) == []


# ── P1.45: Retry + failure persistence tests ─────────────────────────────────


import sqlite3
import tempfile as _tempfile
from pathlib import Path as _Path

from movietrace.feishu.sync import (
    _batch_with_retry,
    _persist_failures,
    _replay_unresolved_failures,
)
from movietrace.db.schema import initialize_database


def _make_test_db() -> tuple[sqlite3.Connection, str]:
    """Return an in-memory (temp-file) connection with migrations applied."""
    tmpdir = _tempfile.mkdtemp()
    db_path = _Path(tmpdir) / "test_p145.db"
    initialize_database(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn, tmpdir


class TestBatchWithRetry:
    """P1.45: _batch_with_retry unit tests."""

    def test_batch_create_retries_on_failure_with_backoff(self):
        """mock batch_create 前 2 次抛异常、第 3 次成功；断言调用次数==3，sleep 总计==3s。"""
        call_count = 0

        def flaky_fn():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RuntimeError("transient error")
            return "ok"

        sleep_calls = []
        with patch("movietrace.feishu.sync.time.sleep", side_effect=lambda s: sleep_calls.append(s)):
            result = _batch_with_retry(flaky_fn, max_retries=3, base_delay=1.0)

        assert result == "ok"
        assert call_count == 3
        # sleep called twice (after attempt 1 and 2): 1s and 2s
        assert len(sleep_calls) == 2
        assert sum(sleep_calls) == pytest.approx(3.0)

    def test_batch_create_gives_up_after_3_retries_and_raises(self):
        """mock 3 次全失败：_batch_with_retry 必须 raise 最后一次异常。"""
        call_count = 0

        def always_fail():
            nonlocal call_count
            call_count += 1
            raise RuntimeError(f"fail #{call_count}")

        with patch("movietrace.feishu.sync.time.sleep"):
            with pytest.raises(RuntimeError, match="fail #3"):
                _batch_with_retry(always_fail, max_retries=3, base_delay=0.0)

        assert call_count == 3


class TestBatchCreateGivesUpAndPersists:
    """P1.45: 全失败时 feishu_sync_failures 写入 + send_alert 调用。"""

    def _minimal_record(self) -> dict:
        return {
            "content_update_id": "discovery:tv:1396:2026-05-17",
            "update_type": "new_discovery",
            "priority": "P1",
            "hot_score": 80.0,
            "title": "Test Show",
            "tmdb_id": "1396",
            "source_data_status": {},
            "event_written_at_utc": "2026-05-17 10:30:00",
            "created_at": "2026-05-17 10:30:00",
            "source_summary_json": json.dumps({"score_breakdown": {}}, ensure_ascii=False),
        }

    @patch("movietrace.feishu.sync.send_alert")
    @patch("movietrace.feishu.sync.send_text")
    @patch("movietrace.feishu.sync.fetch_tenant_access_token")
    @patch("movietrace.feishu.sync.ensure_table_fields")
    @patch("movietrace.feishu.sync._list_records_for_date")
    @patch("movietrace.feishu.sync._list_discovery_records_by_keys")
    @patch("movietrace.feishu.sync.batch_create_records")
    @patch("movietrace.feishu.sync.batch_update_records")
    @patch("movietrace.feishu.sync.time.sleep")
    def test_batch_create_gives_up_after_3_retries_and_persists_failure(
        self, mock_sleep, mock_upd, mock_create, mock_list_discovery, mock_list, mock_ensure,
        mock_token, mock_text, mock_alert,
    ):
        """全失败时 feishu_sync_failures 有对应记录，operation='create'，retry_count=3，send_alert 被调用。"""
        mock_token.return_value = "token"
        mock_ensure.return_value = {"created": [], "existed": [], "renamed": [], "errors": [], "dry_run": False}
        mock_list.return_value = {}
        mock_list_discovery.return_value = {}
        mock_create.side_effect = RuntimeError("api error")

        conn, tmpdir = _make_test_db()
        try:
            record = self._minimal_record()
            with _tempfile.TemporaryDirectory() as td:
                p = _Path(td) / "latest.json"
                p.write_text(json.dumps([record], ensure_ascii=False))
                sync_table(
                    json_path=str(p), run_date="2026-05-17",
                    app_id="a", app_secret="s", app_token="t",
                    table_id="tbl_test",
                    conn=conn,
                    notify_chat_id="chat_xyz",
                )

            rows = conn.execute(
                "select * from feishu_sync_failures where table_id='tbl_test'"
            ).fetchall()
            assert len(rows) >= 1
            assert rows[0]["operation"] == "create"
            assert rows[0]["retry_count"] == 3
            assert rows[0]["resolved_at"] is None

            mock_alert.assert_called()
        finally:
            conn.close()
            import shutil; shutil.rmtree(tmpdir, ignore_errors=True)


class TestBatchUpdatePartialFailureSplitsAndPersists:
    """P1.45: batch update 失败 → 拆单条重试 → 失败条目写入 failures 表。"""

    @patch("movietrace.feishu.sync.send_alert")
    @patch("movietrace.feishu.sync.send_text")
    @patch("movietrace.feishu.sync.fetch_tenant_access_token")
    @patch("movietrace.feishu.sync.ensure_table_fields")
    @patch("movietrace.feishu.sync._list_records_for_date")
    @patch("movietrace.feishu.sync._list_discovery_records_by_keys")
    @patch("movietrace.feishu.sync.batch_create_records")
    @patch("movietrace.feishu.sync.batch_update_records")
    @patch("movietrace.feishu.sync.time.sleep")
    def test_batch_update_partial_failure_splits_and_persists(
        self, mock_sleep, mock_upd, mock_create, mock_list_discovery, mock_list, mock_ensure,
        mock_token, mock_text, mock_alert,
    ):
        """100 条 update 整批失败 → 拆单条 → 5 条仍失败 → 5 条进 feishu_sync_failures。"""
        mock_token.return_value = "token"
        mock_ensure.return_value = {"created": [], "existed": [], "renamed": [], "errors": [], "dry_run": False}
        mock_create.return_value = None

        # 构造 100 条记录（全部已存在 → update 路径）
        # new_discovery with discovery: prefix → goes through existing_discovery lookup
        n = 100
        existing = {f"discovery:tv:{i}:2026-05-17": f"rec_{i}" for i in range(n)}
        mock_list.return_value = {}  # new_season lookup returns nothing
        mock_list_discovery.return_value = existing  # discovery stable key lookup

        # batch_update_records: 整批失败，但单条 rec_0..rec_4 也失败，其余成功
        call_tracker = {"batch_calls": 0}
        fail_ids = {f"rec_{i}" for i in range(5)}

        def smart_update(token, app_token, table_id, records):
            call_tracker["batch_calls"] += 1
            if len(records) > 1:
                raise RuntimeError("batch too large")
            # single-record call
            if records[0]["record_id"] in fail_ids:
                raise RuntimeError("single record failed")
            return None

        mock_upd.side_effect = smart_update

        import json as _json
        records = [
            {
                "content_update_id": f"discovery:tv:{i}:2026-05-17",
                "update_type": "new_discovery",
                "priority": "P2",
                "hot_score": 50.0,
                "title": f"Show {i}",
                "tmdb_id": str(i),
                "source_data_status": {},
                "event_written_at_utc": "2026-05-17 10:30:00",
                "created_at": "2026-05-17 10:30:00",
                "source_summary_json": _json.dumps({"score_breakdown": {}}, ensure_ascii=False),
            }
            for i in range(n)
        ]

        conn, tmpdir = _make_test_db()
        try:
            with _tempfile.TemporaryDirectory() as td:
                p = _Path(td) / "latest.json"
                p.write_text(_json.dumps(records, ensure_ascii=False))
                sync_table(
                    json_path=str(p), run_date="2026-05-17",
                    app_id="a", app_secret="s", app_token="t",
                    table_id="tbl_upd",
                    conn=conn,
                    notify_chat_id="chat_xyz",
                )

            failure_rows = conn.execute(
                "select * from feishu_sync_failures where table_id='tbl_upd' and operation='update'"
            ).fetchall()
            assert len(failure_rows) == 5
        finally:
            conn.close()
            import shutil; shutil.rmtree(tmpdir, ignore_errors=True)


class TestReplayUnresolvedFailures:
    """P1.45: _replay_unresolved_failures tests."""

    def _insert_failure(
        self, conn: sqlite3.Connection, table_id: str, operation: str,
        payload: dict, record_id: str | None = None,
        retry_count: int = 0, resolved_at: str | None = None,
    ) -> int:
        cur = conn.execute(
            """
            insert into feishu_sync_failures
                (table_id, record_id, operation, payload_json, retry_count, resolved_at)
            values (?, ?, ?, ?, ?, ?)
            """,
            (table_id, record_id, operation, json.dumps(payload, ensure_ascii=False),
             retry_count, resolved_at),
        )
        conn.commit()
        return cur.lastrowid

    @patch("movietrace.feishu.sync.batch_create_records")
    @patch("movietrace.feishu.sync.batch_update_records")
    @patch("movietrace.feishu.sync.time.sleep")
    def test_replay_unresolved_failures_runs_first(
        self, mock_sleep, mock_upd, mock_create,
    ):
        """预置 2 条 unresolved 失败；replay 成功后 resolved_at 不为 null。"""
        mock_create.return_value = None
        mock_upd.return_value = None

        conn, tmpdir = _make_test_db()
        try:
            self._insert_failure(conn, "tbl_r", "create", {"title": "A"})
            self._insert_failure(conn, "tbl_r", "create", {"title": "B"})

            result = _replay_unresolved_failures(conn, "tok", "app_tok", "tbl_r")

            assert result["replayed"] == 2
            assert result["resolved"] == 2
            assert result["still_failed"] == 0

            rows = conn.execute(
                "select resolved_at from feishu_sync_failures where table_id='tbl_r'"
            ).fetchall()
            for row in rows:
                assert row[0] is not None, "resolved_at should be set"
        finally:
            conn.close()
            import shutil; shutil.rmtree(tmpdir, ignore_errors=True)

    @patch("movietrace.feishu.sync.batch_create_records")
    @patch("movietrace.feishu.sync.batch_update_records")
    @patch("movietrace.feishu.sync.time.sleep")
    def test_replay_skips_resolved_failures(
        self, mock_sleep, mock_upd, mock_create,
    ):
        """预置 1 条 resolved + 1 条 unresolved；只重做 unresolved 那条。"""
        mock_create.return_value = None
        mock_upd.return_value = None

        conn, tmpdir = _make_test_db()
        try:
            self._insert_failure(
                conn, "tbl_s", "create", {"title": "Resolved"},
                resolved_at="2026-05-21 10:00:00",
            )
            unresolved_id = self._insert_failure(
                conn, "tbl_s", "create", {"title": "Unresolved"},
            )

            result = _replay_unresolved_failures(conn, "tok", "app_tok", "tbl_s")

            assert result["replayed"] == 1
            assert result["resolved"] == 1

            row = conn.execute(
                "select resolved_at from feishu_sync_failures where id=?",
                (unresolved_id,),
            ).fetchone()
            assert row[0] is not None
        finally:
            conn.close()
            import shutil; shutil.rmtree(tmpdir, ignore_errors=True)

    @patch("movietrace.feishu.sync.send_alert")
    @patch("movietrace.feishu.sync.batch_create_records")
    @patch("movietrace.feishu.sync.time.sleep")
    def test_high_retry_count_triggers_alert(
        self, mock_sleep, mock_create, mock_alert,
    ):
        """预置 1 条 retry_count=9，重做仍失败 → retry_count 变 10 → send_alert 被调用。"""
        mock_create.side_effect = RuntimeError("still broken")

        conn, tmpdir = _make_test_db()
        try:
            self._insert_failure(
                conn, "tbl_h", "create", {"title": "Hard Fail"},
                retry_count=9,
            )

            result = _replay_unresolved_failures(
                conn, "tok", "app_tok", "tbl_h",
                notify_chat_id="chat_abc",
                app_id="a", app_secret="s",
            )

            assert result["still_failed"] == 1
            mock_alert.assert_called()
            args = mock_alert.call_args[0]
            assert args[0] == "chat_abc"
        finally:
            conn.close()
            import shutil; shutil.rmtree(tmpdir, ignore_errors=True)


# ── P1.57h: Discovery stable key upsert tests ─────────────────────────────────


class TestDiscoveryStableKeyUpsert:
    """P1.57h: discovery records use stable key (no date) for upsert."""

    ENSURE_OK = {"created": [], "existed": [], "renamed": [], "errors": [], "dry_run": False}

    def _make_discovery_record(self, tmdb_id: str = "1396", run_date: str = "2026-05-17", **kwargs) -> dict:
        base = {
            "content_update_id": f"discovery:tv:{tmdb_id}",
            "update_type": "new_discovery",
            "priority": "P2",
            "hot_score": 75.0,
            "title": "Grey's Anatomy",
            "tmdb_id": tmdb_id,
            "source_data_status": {},
            "event_written_at_utc": f"{run_date} 10:30:00",
            "created_at": f"{run_date} 10:30:00",
            "source_summary_json": json.dumps({"score_breakdown": {}}, ensure_ascii=False),
        }
        base.update(kwargs)
        return base

    def _make_new_season_record(self, tmdb_tv_id: str = "2190", run_date: str = "2026-05-17", **kwargs) -> dict:
        base = {
            "content_update_id": f"new_season:{tmdb_tv_id}:S5",
            "update_type": "new_season",
            "priority": "P1",
            "hot_score": 90.0,
            "title": "Survivor",
            "tmdb_tv_id": tmdb_tv_id,
            "source_data_status": {},
            "event_written_at_utc": f"{run_date} 10:30:00",
            "created_at": f"{run_date} 10:30:00",
            "source_summary_json": json.dumps({"score_breakdown": {}}, ensure_ascii=False),
        }
        base.update(kwargs)
        return base

    @patch("movietrace.feishu.sync.fetch_tenant_access_token")
    @patch("movietrace.feishu.sync.ensure_table_fields")
    @patch("movietrace.feishu.sync._list_records_for_date")
    @patch("movietrace.feishu.sync._list_discovery_records_by_keys")
    @patch("movietrace.feishu.sync.batch_create_records")
    @patch("movietrace.feishu.sync.batch_update_records")
    def test_same_discovery_key_across_two_days_updates_not_creates(
        self,
        mock_batch_update,
        mock_batch_create,
        mock_list_discovery,
        mock_list_records,
        mock_ensure_fields,
        mock_fetch_token,
    ):
        """验收1: 同一 discovery key 跨两天 sync，第二天 mock 命中稳定键 → update 而非 create。"""
        mock_fetch_token.return_value = "token"
        mock_ensure_fields.return_value = self.ENSURE_OK
        mock_list_records.return_value = {}
        # Day 2: discovery record already exists by stable key
        mock_list_discovery.return_value = {"discovery:tv:1396": "existing_record_id"}

        record = self._make_discovery_record(run_date="2026-05-18")
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir) / "latest.json"
            p.write_text(json.dumps([record], ensure_ascii=False))
            result = sync_table(
                json_path=str(p), run_date="2026-05-18",
                app_id="a", app_secret="s", app_token="t", table_id="tbl",
            )

        assert result["updated"] == 1
        assert result["created"] == 0
        mock_batch_update.assert_called_once()
        mock_batch_create.assert_not_called()
        # Verify record_id passed to update is the existing one
        updates = mock_batch_update.call_args[0][3]
        assert updates[0]["record_id"] == "existing_record_id"

    @patch("movietrace.feishu.sync.fetch_tenant_access_token")
    @patch("movietrace.feishu.sync.ensure_table_fields")
    @patch("movietrace.feishu.sync._list_records_for_date")
    @patch("movietrace.feishu.sync._list_discovery_records_by_keys")
    @patch("movietrace.feishu.sync.batch_create_records")
    @patch("movietrace.feishu.sync.batch_update_records")
    def test_discovery_update_excludes_ops_fields(
        self,
        mock_batch_update,
        mock_batch_create,
        mock_list_discovery,
        mock_list_records,
        mock_ensure_fields,
        mock_fetch_token,
    ):
        """验收2: 更新已有 discovery 行时不覆盖运营状态、供应商状态、运营备注。"""
        mock_fetch_token.return_value = "token"
        mock_ensure_fields.return_value = self.ENSURE_OK
        mock_list_records.return_value = {}
        mock_list_discovery.return_value = {"discovery:tv:1396": "rec_abc"}

        record = self._make_discovery_record(
            source_summary_json=json.dumps({
                "score_breakdown": {},
                "ops_note": "auto degraded",
            }, ensure_ascii=False),
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir) / "latest.json"
            p.write_text(json.dumps([record], ensure_ascii=False))
            sync_table(
                json_path=str(p), run_date="2026-05-17",
                app_id="a", app_secret="s", app_token="t", table_id="tbl",
            )

        mock_batch_update.assert_called_once()
        updates = mock_batch_update.call_args[0][3]
        fields = updates[0]["fields"]
        assert "运营状态" not in fields
        assert "供应商状态" not in fields
        assert "运营备注" not in fields
        assert "负责人" not in fields

    @patch("movietrace.feishu.sync.fetch_tenant_access_token")
    @patch("movietrace.feishu.sync.ensure_table_fields")
    @patch("movietrace.feishu.sync._list_records_for_date")
    @patch("movietrace.feishu.sync._list_discovery_records_by_keys")
    @patch("movietrace.feishu.sync.batch_create_records")
    @patch("movietrace.feishu.sync.batch_update_records")
    def test_discovery_update_writes_date_and_count_fields(
        self,
        mock_batch_update,
        mock_batch_create,
        mock_list_discovery,
        mock_list_records,
        mock_ensure_fields,
        mock_fetch_token,
    ):
        """验收3: 更新 discovery 时写入最近发现日期和发现次数。"""
        mock_fetch_token.return_value = "token"
        mock_ensure_fields.return_value = self.ENSURE_OK
        mock_list_records.return_value = {}
        mock_list_discovery.return_value = {"discovery:tv:1396": "rec_xyz"}

        record = self._make_discovery_record(
            last_discovered_date="2026-05-18",
            discovery_count=3,
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir) / "latest.json"
            p.write_text(json.dumps([record], ensure_ascii=False))
            sync_table(
                json_path=str(p), run_date="2026-05-18",
                app_id="a", app_secret="s", app_token="t", table_id="tbl",
            )

        mock_batch_update.assert_called_once()
        updates = mock_batch_update.call_args[0][3]
        fields = updates[0]["fields"]
        assert "最近发现日期" in fields
        assert isinstance(fields["最近发现日期"], int)
        assert "发现次数" in fields
        assert fields["发现次数"] == 3

    @patch("movietrace.feishu.sync.fetch_tenant_access_token")
    @patch("movietrace.feishu.sync.ensure_table_fields")
    @patch("movietrace.feishu.sync._list_records_for_date")
    @patch("movietrace.feishu.sync._list_discovery_records_by_keys")
    @patch("movietrace.feishu.sync.batch_create_records")
    @patch("movietrace.feishu.sync.batch_update_records")
    def test_new_season_uses_event_key_path_unaffected(
        self,
        mock_batch_update,
        mock_batch_create,
        mock_list_discovery,
        mock_list_records,
        mock_ensure_fields,
        mock_fetch_token,
    ):
        """验收4: new_season 行走旧事件键路径，不受 discovery 稳定 key 逻辑干扰。"""
        mock_fetch_token.return_value = "token"
        mock_ensure_fields.return_value = self.ENSURE_OK
        # new_season record already exists under event key
        mock_list_records.return_value = {
            "2026-05-17|new_season:2190:S5": "season_rec_id"
        }
        mock_list_discovery.return_value = {}

        record = self._make_new_season_record(run_date="2026-05-17")
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir) / "latest.json"
            p.write_text(json.dumps([record], ensure_ascii=False))
            result = sync_table(
                json_path=str(p), run_date="2026-05-17",
                app_id="a", app_secret="s", app_token="t", table_id="tbl",
            )

        assert result["updated"] == 1
        assert result["created"] == 0
        mock_batch_update.assert_called_once()
        updates = mock_batch_update.call_args[0][3]
        assert updates[0]["record_id"] == "season_rec_id"
        # new_season update DOES include all fields (no ops field exclusion)
        fields = updates[0]["fields"]
        assert "同步批次" in fields
        assert fields["同步批次"] == "2026-05-17"

    @patch("movietrace.feishu.sync.fetch_tenant_access_token")
    @patch("movietrace.feishu.sync.ensure_table_fields")
    @patch("movietrace.feishu.sync._list_records_for_date")
    @patch("movietrace.feishu.sync._list_discovery_records_by_keys")
    @patch("movietrace.feishu.sync.batch_create_records")
    @patch("movietrace.feishu.sync.batch_update_records")
    def test_sync_batch_field_written_as_run_date_on_create_and_update(
        self,
        mock_batch_update,
        mock_batch_create,
        mock_list_discovery,
        mock_list_records,
        mock_ensure_fields,
        mock_fetch_token,
    ):
        """验收5: 同步批次写为最新 run_date（create 和 update 都写）。"""
        mock_fetch_token.return_value = "token"
        mock_ensure_fields.return_value = self.ENSURE_OK
        # One new (create), one existing (update)
        mock_list_records.return_value = {}
        mock_list_discovery.return_value = {"discovery:tv:9999": "existing_id"}

        records = [
            self._make_discovery_record(tmdb_id="1396", run_date="2026-05-20"),  # new → create
            self._make_discovery_record(tmdb_id="9999", run_date="2026-05-20"),  # existing → update
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir) / "latest.json"
            p.write_text(json.dumps(records, ensure_ascii=False))
            result = sync_table(
                json_path=str(p), run_date="2026-05-20",
                app_id="a", app_secret="s", app_token="t", table_id="tbl",
            )

        assert result["created"] == 1
        assert result["updated"] == 1

        # Check create record has 同步批次 = run_date
        create_fields = mock_batch_create.call_args[0][3][0]["fields"]
        assert create_fields["同步批次"] == "2026-05-20"

        # Check update record has 同步批次 = run_date (system field, included in update)
        updates = mock_batch_update.call_args[0][3]
        update_fields = updates[0]["fields"]
        assert update_fields["同步批次"] == "2026-05-20"

    @patch("movietrace.feishu.sync.fetch_tenant_access_token")
    @patch("movietrace.feishu.sync.ensure_table_fields")
    @patch("movietrace.feishu.sync._list_records_for_date")
    @patch("movietrace.feishu.sync._list_discovery_records_by_keys")
    @patch("movietrace.feishu.sync.batch_create_records")
    @patch("movietrace.feishu.sync.batch_update_records")
    def test_discovery_create_writes_all_date_fields(
        self,
        mock_batch_update,
        mock_batch_create,
        mock_list_discovery,
        mock_list_records,
        mock_ensure_fields,
        mock_fetch_token,
    ):
        """验收: 新创建 discovery 行时写入首次发现日期、最近发现日期、发现次数。"""
        mock_fetch_token.return_value = "token"
        mock_ensure_fields.return_value = self.ENSURE_OK
        mock_list_records.return_value = {}
        mock_list_discovery.return_value = {}  # no existing record → create

        record = self._make_discovery_record(
            first_discovered_date="2026-05-15",
            last_discovered_date="2026-05-18",
            discovery_count=4,
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir) / "latest.json"
            p.write_text(json.dumps([record], ensure_ascii=False))
            result = sync_table(
                json_path=str(p), run_date="2026-05-18",
                app_id="a", app_secret="s", app_token="t", table_id="tbl",
            )

        assert result["created"] == 1
        mock_batch_create.assert_called_once()
        fields = mock_batch_create.call_args[0][3][0]["fields"]
        assert "首次发现日期" in fields
        assert isinstance(fields["首次发现日期"], int)
        assert "最近发现日期" in fields
        assert isinstance(fields["最近发现日期"], int)
        assert "发现次数" in fields
        assert fields["发现次数"] == 4

    @patch("movietrace.feishu.sync.fetch_tenant_access_token")
    @patch("movietrace.feishu.sync.ensure_table_fields")
    @patch("movietrace.feishu.sync._list_records_for_date")
    @patch("movietrace.feishu.sync._list_discovery_records_by_keys")
    @patch("movietrace.feishu.sync.batch_create_records")
    @patch("movietrace.feishu.sync.batch_update_records")
    def test_discovery_content_update_id_written_as_stable_key(
        self,
        mock_batch_update,
        mock_batch_create,
        mock_list_discovery,
        mock_list_records,
        mock_ensure_fields,
        mock_fetch_token,
    ):
        """验收: create 时 content_update_id 写入稳定 key（不含日期前缀）。"""
        mock_fetch_token.return_value = "token"
        mock_ensure_fields.return_value = self.ENSURE_OK
        mock_list_records.return_value = {}
        mock_list_discovery.return_value = {}

        record = self._make_discovery_record()
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir) / "latest.json"
            p.write_text(json.dumps([record], ensure_ascii=False))
            sync_table(
                json_path=str(p), run_date="2026-05-17",
                app_id="a", app_secret="s", app_token="t", table_id="tbl",
            )

        fields = mock_batch_create.call_args[0][3][0]["fields"]
        assert fields["content_update_id"] == "discovery:tv:1396"
        # Must NOT contain the run_date prefix
        assert "2026-05-17" not in fields["content_update_id"]

    @patch("movietrace.feishu.sync.fetch_tenant_access_token")
    @patch("movietrace.feishu.sync.ensure_table_fields")
    @patch("movietrace.feishu.sync._list_records_for_date")
    @patch("movietrace.feishu.sync._list_discovery_records_by_keys")
    @patch("movietrace.feishu.sync.batch_create_records")
    @patch("movietrace.feishu.sync.batch_update_records")
    def test_discovery_update_does_not_overwrite_first_seen_fields(
        self,
        mock_batch_update,
        mock_batch_create,
        mock_list_discovery,
        mock_list_records,
        mock_ensure_fields,
        mock_fetch_token,
    ):
        """A4: discovery update branch must NOT include '发现日期' or '首次发现日期'.
        Overwriting these each day would make every sync look like first discovery.
        Update branch MUST include '最近发现日期' and '发现次数'.
        """
        mock_fetch_token.return_value = "token"
        mock_ensure_fields.return_value = self.ENSURE_OK
        mock_list_records.return_value = {}
        # Existing record → update path
        mock_list_discovery.return_value = {"discovery:tv:1396": "rec_a4_test"}

        record = self._make_discovery_record(
            last_discovered_date="2026-05-20",
            first_discovered_date="2026-05-10",
            discovery_count=5,
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir) / "latest.json"
            p.write_text(json.dumps([record], ensure_ascii=False))
            sync_table(
                json_path=str(p), run_date="2026-05-20",
                app_id="a", app_secret="s", app_token="t", table_id="tbl",
            )

        mock_batch_update.assert_called_once()
        updates = mock_batch_update.call_args[0][3]
        fields = updates[0]["fields"]
        # A4: must NOT overwrite first-seen fields
        assert "发现日期" not in fields, (
            "'发现日期' must not appear in discovery update fields — "
            "it would overwrite the first-seen date with today's run_date"
        )
        assert "首次发现日期" not in fields, (
            "'首次发现日期' must not appear in discovery update fields"
        )
        # Must still update the rolling stats
        assert "最近发现日期" in fields
        assert "发现次数" in fields
        assert fields["发现次数"] == 5
