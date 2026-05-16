"""Tests for feishu/sync.py pure functions and feishu/_http.py multipart helpers."""

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from movietrace.feishu.sync import _to_epoch_ms, _derive_content_type

UTC = timezone.utc
CST = ZoneInfo("Asia/Shanghai")


# ── _to_epoch_ms (P1.21.8) ───────────────────────────────────────────────────

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


# ── build_multipart_body (P1.21.9) ────────────────────────────────────────────

class TestBuildMultipartBody(unittest.TestCase):
    def _parse_parts(self, body: bytes, boundary: str) -> list[dict]:
        sep = f"--{boundary}\r\n".encode()
        body = body.rstrip(b"\r\n")
        assert body.endswith(f"--{boundary}--".encode()), "missing final boundary"
        inner = body[: body.rfind(f"--{boundary}--".encode())]
        raw_parts = inner.split(sep)
        parts = []
        for rp in raw_parts:
            rp = rp.strip(b"\r\n")
            if not rp:
                continue
            header_block, _, content = rp.partition(b"\r\n\r\n")
            headers = {}
            for line in header_block.decode("utf-8").splitlines():
                if ":" in line:
                    k, _, v = line.partition(":")
                    headers[k.strip()] = v.strip()
            content = content.rstrip(b"\r\n")
            parts.append({"headers": headers, "content": content})
        return parts

    def test_text_fields_present(self):
        from movietrace.feishu._http import build_multipart_body
        body, boundary = build_multipart_body({"file_name": "test.md", "size": "42"})
        parts = self._parse_parts(body, boundary)
        names = [p["headers"].get("Content-Disposition", "") for p in parts]
        self.assertTrue(any('name="file_name"' in n for n in names))
        self.assertTrue(any('name="size"' in n for n in names))

    def test_text_field_value_preserved(self):
        from movietrace.feishu._http import build_multipart_body
        body, boundary = build_multipart_body({"parent_type": "ccm_import_open"})
        parts = self._parse_parts(body, boundary)
        self.assertEqual(len(parts), 1)
        self.assertEqual(parts[0]["content"], b"ccm_import_open")

    def test_binary_file_field(self):
        from movietrace.feishu._http import build_multipart_body
        data = b"\xff\xfe hello world"
        body, boundary = build_multipart_body({
            "file": (data, "report.md", "application/octet-stream"),
        })
        parts = self._parse_parts(body, boundary)
        self.assertEqual(len(parts), 1)
        disp = parts[0]["headers"].get("Content-Disposition", "")
        self.assertIn('name="file"', disp)
        self.assertIn('filename="report.md"', disp)
        self.assertEqual(parts[0]["content"], data)
        self.assertEqual(parts[0]["headers"].get("Content-Type", ""), "application/octet-stream")

    def test_mixed_fields_and_file(self):
        from movietrace.feishu._http import build_multipart_body
        file_data = b"# Hello\n"
        body, boundary = build_multipart_body({
            "file_name": "hello.md",
            "size": str(len(file_data)),
            "file": (file_data, "hello.md", "application/octet-stream"),
        })
        parts = self._parse_parts(body, boundary)
        self.assertEqual(len(parts), 3)
        self.assertIn(boundary, body.decode("latin-1"))

    def test_boundary_is_unique_per_call(self):
        from movietrace.feishu._http import build_multipart_body
        _, b1 = build_multipart_body({"x": "1"})
        _, b2 = build_multipart_body({"x": "1"})
        self.assertNotEqual(b1, b2)

    def test_unicode_text_field(self):
        from movietrace.feishu._http import build_multipart_body
        body, boundary = build_multipart_body({"title": "飞书文档测试"})
        parts = self._parse_parts(body, boundary)
        self.assertEqual(parts[0]["content"].decode("utf-8"), "飞书文档测试")


# ── sync_doc import task flow (P1.21.9) ──────────────────────────────────────

class TestSyncDoc(unittest.TestCase):
    def _make_poll_resp(self, job_status=0, token="doc_abc", url="https://feishu.cn/docx/doc_abc"):
        return {"code": 0, "data": {"result": {"job_status": job_status, "token": token, "url": url}}}

    def test_dry_run_returns_empty(self):
        from movietrace.feishu.sync import sync_doc
        import tempfile, os
        with tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False) as f:
            f.write("# Test\n"); tmp = f.name
        try:
            result = sync_doc(tmp, "My Title", dry_run=True)
            self.assertEqual(result["doc_url"], "")
            self.assertTrue(result.get("dry_run"))
        finally:
            os.unlink(tmp)

    def test_raises_without_credentials(self):
        from movietrace.feishu.sync import sync_doc
        import tempfile, os
        with tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False) as f:
            f.write("# Test\n"); tmp = f.name
        try:
            with self.assertRaises(RuntimeError):
                sync_doc(tmp, "Title")
        finally:
            os.unlink(tmp)

    def test_happy_path_immediate_success(self):
        from movietrace.feishu.sync import sync_doc
        import tempfile, os
        with tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False) as f:
            f.write("# Report\n"); tmp = f.name
        try:
            import_resp = {"code": 0, "data": {"ticket": "ticket_xyz"}}
            poll_resp = self._make_poll_resp(job_status=0, token="tok123", url="https://feishu.cn/docx/tok123")
            with patch("movietrace.feishu.sync.fetch_tenant_access_token", return_value="bearer"):
                with patch("movietrace.feishu.sync.upload_media_file", return_value="file_tok"):
                    with patch("movietrace.feishu.sync.request_json") as mock_rj:
                        mock_rj.side_effect = [import_resp, poll_resp]
                        with patch("movietrace.feishu.sync.time.sleep"):
                            result = sync_doc(tmp, "My Doc", "folder_abc", app_id="aid", app_secret="asec")
            self.assertEqual(result["doc_token"], "tok123")
            self.assertIn("tok123", result["doc_url"])
        finally:
            os.unlink(tmp)

    def test_polls_until_done(self):
        from movietrace.feishu.sync import sync_doc
        import tempfile, os
        with tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False) as f:
            f.write("# Content\n"); tmp = f.name
        try:
            import_resp = {"code": 0, "data": {"ticket": "tck"}}
            processing = {"code": 0, "data": {"result": {"job_status": 2}}}
            done = self._make_poll_resp(job_status=0, token="done_tok")
            with patch("movietrace.feishu.sync.fetch_tenant_access_token", return_value="tok"):
                with patch("movietrace.feishu.sync.upload_media_file", return_value="ft"):
                    with patch("movietrace.feishu.sync.request_json") as mock_rj:
                        mock_rj.side_effect = [import_resp, processing, processing, done]
                        with patch("movietrace.feishu.sync.time.sleep"):
                            result = sync_doc(tmp, "T", app_id="a", app_secret="s")
            self.assertEqual(result["doc_token"], "done_tok")
            self.assertEqual(mock_rj.call_count, 4)
        finally:
            os.unlink(tmp)

    def test_raises_on_job_error(self):
        from movietrace.feishu.sync import sync_doc
        import tempfile, os
        with tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False) as f:
            f.write("# Content\n"); tmp = f.name
        try:
            import_resp = {"code": 0, "data": {"ticket": "tck"}}
            error_resp = {"code": 0, "data": {"result": {"job_status": 3, "job_error_msg": "format error"}}}
            with patch("movietrace.feishu.sync.fetch_tenant_access_token", return_value="tok"):
                with patch("movietrace.feishu.sync.upload_media_file", return_value="ft"):
                    with patch("movietrace.feishu.sync.request_json") as mock_rj:
                        mock_rj.side_effect = [import_resp, error_resp]
                        with patch("movietrace.feishu.sync.time.sleep"):
                            with self.assertRaises(RuntimeError) as ctx:
                                sync_doc(tmp, "T", app_id="a", app_secret="s")
            self.assertIn("job_status=3", str(ctx.exception))
        finally:
            os.unlink(tmp)

    def test_permission_error_raises_with_guidance(self):
        from movietrace.feishu.sync import sync_doc
        import tempfile, os
        with tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False) as f:
            f.write("# Content\n"); tmp = f.name
        try:
            with patch("movietrace.feishu.sync.fetch_tenant_access_token", return_value="tok"):
                with patch("movietrace.feishu.sync.upload_media_file", side_effect=RuntimeError(
                    "Feishu upload permission denied (code=99991663): no permission. "
                    "Grant the app 'drive:drive' scope in the Feishu console."
                )):
                    with self.assertRaises(RuntimeError) as ctx:
                        sync_doc(tmp, "T", app_id="a", app_secret="s")
            self.assertIn("drive:drive", str(ctx.exception))
        finally:
            os.unlink(tmp)


if __name__ == "__main__":
    unittest.main()
