"""Unit tests for feishu/schema_setup.py (P1.24-D).

Mock Feishu API calls to avoid real HTTP requests.
"""

from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock

from movietrace.feishu.schema_setup import (
    list_table_fields,
    create_table_field,
    rename_table_field,
    ensure_table_fields,
    REQUIRED_FIELDS_FOR_DISCOVERY_TABLE,
    FIELD_RENAMES,
)


class TestListTableFields:
    """Test list_table_fields function."""

    @patch("movietrace.feishu.schema_setup.request_json")
    def test_list_table_fields_single_page(self, mock_request_json):
        """Test listing fields with single page."""
        mock_request_json.return_value = {
            "code": 0,
            "data": {
                "items": [
                    {"field_id": "f1", "field_name": "发现日期", "type": 5},
                    {"field_id": "f2", "field_name": "标题", "type": 1},
                ],
                "page_token": None,
            },
        }

        result = list_table_fields(token="mock_token", app_token="app1", table_id="tbl1")
        assert len(result) == 2
        assert result[0]["field_name"] == "发现日期"
        assert result[1]["field_name"] == "标题"

    @patch("movietrace.feishu.schema_setup.request_json")
    def test_list_table_fields_pagination(self, mock_request_json):
        """Test listing fields with pagination."""
        mock_request_json.side_effect = [
            {
                "code": 0,
                "data": {
                    "items": [
                        {"field_id": "f1", "field_name": "发现日期", "type": 5},
                    ],
                    "has_more": True,
                    "page_token": "next_page",
                },
            },
            {
                "code": 0,
                "data": {
                    "items": [
                        {"field_id": "f2", "field_name": "标题", "type": 1},
                    ],
                    "has_more": False,
                    "page_token": None,
                },
            },
        ]

        result = list_table_fields(token="mock_token", app_token="app1", table_id="tbl1")
        assert len(result) == 2
        assert mock_request_json.call_count == 2

    @patch("movietrace.feishu.schema_setup.request_json")
    def test_list_table_fields_permission_error(self, mock_request_json):
        """Test permission error (99991661)."""
        mock_request_json.return_value = {
            "code": 99991661,
            "msg": "Permission denied",
        }

        with pytest.raises(RuntimeError) as exc_info:
            list_table_fields(token="mock_token", app_token="app1", table_id="tbl1")
        assert "permission denied" in str(exc_info.value).lower()
        assert "99991661" in str(exc_info.value)

    @patch("movietrace.feishu.schema_setup.request_json")
    def test_list_table_fields_other_error(self, mock_request_json):
        """Test other API error."""
        mock_request_json.return_value = {
            "code": 12345,
            "msg": "Unknown error",
        }

        with pytest.raises(RuntimeError) as exc_info:
            list_table_fields(token="mock_token", app_token="app1", table_id="tbl1")
        assert "12345" in str(exc_info.value)


class TestCreateTableField:
    """Test create_table_field function."""

    @patch("movietrace.feishu.schema_setup.request_json")
    def test_create_table_field_success(self, mock_request_json):
        """Test successful field creation."""
        mock_request_json.return_value = {
            "code": 0,
            "data": {
                "field_id": "new_f1",
                "field_name": "新字段",
                "type": 2,
            },
        }

        result = create_table_field(
            token="mock_token",
            app_token="app1",
            table_id="tbl1",
            field_name="新字段",
            field_type=2,
        )
        assert result["field_id"] == "new_f1"
        assert result["field_name"] == "新字段"

    @patch("movietrace.feishu.schema_setup.request_json")
    def test_create_table_field_permission_error(self, mock_request_json):
        """Test permission error (99991663)."""
        mock_request_json.return_value = {
            "code": 99991663,
            "msg": "No write scope",
        }

        with pytest.raises(RuntimeError) as exc_info:
            create_table_field(
                token="mock_token",
                app_token="app1",
                table_id="tbl1",
                field_name="新字段",
                field_type=2,
            )
        assert "permission denied" in str(exc_info.value).lower()
        assert "99991663" in str(exc_info.value)


class TestRenameTableField:
    """Test rename_table_field function."""

    @patch("movietrace.feishu.schema_setup.request_json")
    def test_rename_table_field_success(self, mock_request_json):
        """Test successful field rename."""
        mock_request_json.return_value = {
            "code": 0,
            "data": {
                "field_id": "f1",
                "field_name": "新名称",
                "type": 2,
            },
        }

        result = rename_table_field(
            token="mock_token",
            app_token="app1",
            table_id="tbl1",
            field_id="f1",
            new_name="新名称",
        )
        assert result["field_name"] == "新名称"

    @patch("movietrace.feishu.schema_setup.request_json")
    def test_rename_table_field_permission_error(self, mock_request_json):
        """Test permission error (1061045)."""
        mock_request_json.return_value = {
            "code": 1061045,
            "msg": "No permission",
        }

        with pytest.raises(RuntimeError) as exc_info:
            rename_table_field(
                token="mock_token",
                app_token="app1",
                table_id="tbl1",
                field_id="f1",
                new_name="新名称",
            )
        assert "permission denied" in str(exc_info.value).lower()
        assert "1061045" in str(exc_info.value)


class TestEnsureTableFields:
    """Test ensure_table_fields function."""

    @patch("movietrace.feishu.schema_setup.fetch_tenant_access_token")
    @patch("movietrace.feishu.schema_setup.list_table_fields")
    def test_ensure_fields_dry_run(self, mock_list_fields, mock_fetch_token):
        """Test dry_run=True returns plan without calling write APIs."""
        mock_fetch_token.return_value = "mock_token"
        mock_list_fields.return_value = [
            {"field_id": "f1", "field_name": "发现日期", "type": 5},
            {"field_id": "f2", "field_name": "标题", "type": 1},
        ]

        result = ensure_table_fields(
            app_id="app_id",
            app_secret="app_secret",
            app_token="app1",
            table_id="tbl1",
            required=[
                ("发现日期", 5),
                ("新字段", 2),
            ],
            renames=[],
            dry_run=True,
        )

        assert result["dry_run"] is True
        # 新字段应该在 created plan 中
        created_names = [f["field_name"] for f in result["created"]]
        assert "新字段" in created_names
        # 发现日期应该在 existed 中
        existed_names = [f["field_name"] for f in result["existed"]]
        assert "发现日期" in existed_names

    @patch("movietrace.feishu.schema_setup.fetch_tenant_access_token")
    @patch("movietrace.feishu.schema_setup.list_table_fields")
    @patch("movietrace.feishu.schema_setup.create_table_field")
    def test_ensure_fields_creates_missing(self, mock_create, mock_list_fields, mock_fetch_token):
        """Test creating missing fields."""
        mock_fetch_token.return_value = "mock_token"
        mock_list_fields.return_value = [
            {"field_id": "f1", "field_name": "发现日期", "type": 5},
            {"field_id": "f2", "field_name": "标题", "type": 1},
        ]
        mock_create.return_value = {
            "field_id": "f3",
            "field_name": "新字段",
            "type": 2,
        }

        result = ensure_table_fields(
            app_id="app_id",
            app_secret="app_secret",
            app_token="app1",
            table_id="tbl1",
            required=[
                ("发现日期", 5),
                ("新字段", 2),
            ],
            renames=[],
            dry_run=False,
        )

        # 新字段应该被创建
        assert len(result["created"]) == 1
        assert result["created"][0]["field_name"] == "新字段"
        # 发现日期应该在 existed 中
        assert len(result["existed"]) == 1
        assert result["existed"][0]["field_name"] == "发现日期"
        # 应该调用 create 一次
        assert mock_create.call_count == 1

    @patch("movietrace.feishu.schema_setup.fetch_tenant_access_token")
    @patch("movietrace.feishu.schema_setup.list_table_fields")
    @patch("movietrace.feishu.schema_setup.rename_table_field")
    def test_ensure_fields_renames_legacy_field(self, mock_rename, mock_list_fields, mock_fetch_token):
        """Test renaming legacy field."""
        mock_fetch_token.return_value = "mock_token"
        mock_list_fields.return_value = [
            {"field_id": "f1", "field_name": "季号", "type": 2},
            {"field_id": "f2", "field_name": "标题", "type": 1},
        ]
        mock_rename.return_value = {
            "field_id": "f1",
            "field_name": "在播最新季",
            "type": 2,
        }

        result = ensure_table_fields(
            app_id="app_id",
            app_secret="app_secret",
            app_token="app1",
            table_id="tbl1",
            required=[
                ("在播最新季", 2),
                ("标题", 1),
            ],
            renames=[("季号", "在播最新季")],
            dry_run=False,
        )

        # 应该进行了重命名
        assert len(result["renamed"]) == 1
        assert result["renamed"][0]["old_name"] == "季号"
        assert result["renamed"][0]["new_name"] == "在播最新季"
        # 重命名后的字段应该视为已存在,不再创建
        assert len(result["created"]) == 0
        # 调用 rename 一次
        assert mock_rename.call_count == 1

    @patch("movietrace.feishu.schema_setup.fetch_tenant_access_token")
    @patch("movietrace.feishu.schema_setup.list_table_fields")
    def test_ensure_fields_rename_target_exists(self, mock_list_fields, mock_fetch_token):
        """Test rename when target name already exists."""
        mock_fetch_token.return_value = "mock_token"
        mock_list_fields.return_value = [
            {"field_id": "f1", "field_name": "季号", "type": 2},
            {"field_id": "f2", "field_name": "在播最新季", "type": 2},
        ]

        result = ensure_table_fields(
            app_id="app_id",
            app_secret="app_secret",
            app_token="app1",
            table_id="tbl1",
            required=[
                ("在播最新季", 2),
            ],
            renames=[("季号", "在播最新季")],
            dry_run=False,
        )

        # 应该有 error 表示无法重命名
        assert len(result["errors"]) > 0
        assert "Cannot rename" in result["errors"][0]
        # 没有进行重命名
        assert len(result["renamed"]) == 0

    @patch("movietrace.feishu.schema_setup.fetch_tenant_access_token")
    @patch("movietrace.feishu.schema_setup.list_table_fields")
    @patch("movietrace.feishu.schema_setup.create_table_field")
    def test_ensure_fields_permission_error_on_create(self, mock_create, mock_list_fields, mock_fetch_token):
        """Test handling permission error during field creation."""
        mock_fetch_token.return_value = "mock_token"
        mock_list_fields.return_value = [
            {"field_id": "f1", "field_name": "发现日期", "type": 5},
        ]
        mock_create.side_effect = RuntimeError(
            "Feishu field creation permission denied (code=99991661): "
            "Grant the app 'bitable:app' + 'bitable:app:fields:write' scope in the Feishu console."
        )

        with pytest.raises(RuntimeError) as exc_info:
            ensure_table_fields(
                app_id="app_id",
                app_secret="app_secret",
                app_token="app1",
                table_id="tbl1",
                required=[
                    ("新字段", 2),
                ],
                renames=[],
                dry_run=False,
            )

        assert "99991661" in str(exc_info.value)
        assert "permission" in str(exc_info.value).lower()

    @patch("movietrace.feishu.schema_setup.fetch_tenant_access_token")
    @patch("movietrace.feishu.schema_setup.list_table_fields")
    @patch("movietrace.feishu.schema_setup.create_table_field")
    def test_ensure_fields_all_exist(self, mock_create, mock_list_fields, mock_fetch_token):
        """Test when all required fields already exist (idempotent)."""
        mock_fetch_token.return_value = "mock_token"
        mock_list_fields.return_value = [
            {"field_id": "f1", "field_name": "发现日期", "type": 5},
            {"field_id": "f2", "field_name": "标题", "type": 1},
            {"field_id": "f3", "field_name": "新字段", "type": 2},
        ]

        result = ensure_table_fields(
            app_id="app_id",
            app_secret="app_secret",
            app_token="app1",
            table_id="tbl1",
            required=[
                ("发现日期", 5),
                ("标题", 1),
                ("新字段", 2),
            ],
            renames=[],
            dry_run=False,
        )

        # 无创建、无重命名
        assert len(result["created"]) == 0
        assert len(result["renamed"]) == 0
        # 所有字段应该在 existed 中
        assert len(result["existed"]) == 3
        # 不应该调用 create
        assert mock_create.call_count == 0
