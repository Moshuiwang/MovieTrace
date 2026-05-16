"""Tests for movietrace.feishu._http multipart helpers and sync_doc import flow."""
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))


# ── build_multipart_body ──────────────────────────────────────────────────────

class TestBuildMultipartBody(unittest.TestCase):
    def _parse_parts(self, body: bytes, boundary: str) -> list[dict]:
        """Parse multipart body into a list of {headers, content} dicts."""
        sep = f"--{boundary}\r\n".encode()
        end = f"--{boundary}--\r\n".encode()
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
        ct = parts[0]["headers"].get("Content-Type", "")
        self.assertEqual(ct, "application/octet-stream")

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
        # Check boundary string is in Content-Type header
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


# ── sync_doc (import task flow) ───────────────────────────────────────────────

class TestSyncDoc(unittest.TestCase):
    def _make_poll_resp(self, job_status=0, token="doc_abc", url="https://feishu.cn/docx/doc_abc"):
        return {
            "code": 0,
            "data": {
                "result": {
                    "job_status": job_status,
                    "token": token,
                    "url": url,
                }
            },
        }

    def test_dry_run_returns_empty(self):
        from movietrace.feishu.sync import sync_doc
        import tempfile, os

        with tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False) as f:
            f.write("# Test\n")
            tmp = f.name
        try:
            result = sync_doc(tmp, "My Title", dry_run=True)
            self.assertEqual(result["doc_url"], "")
            self.assertEqual(result["doc_token"], "")
            self.assertTrue(result.get("dry_run"))
        finally:
            os.unlink(tmp)

    def test_raises_without_credentials(self):
        from movietrace.feishu.sync import sync_doc
        import tempfile, os

        with tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False) as f:
            f.write("# Test\n")
            tmp = f.name
        try:
            with self.assertRaises(RuntimeError):
                sync_doc(tmp, "Title")
        finally:
            os.unlink(tmp)

    def test_happy_path_immediate_success(self):
        from movietrace.feishu.sync import sync_doc
        import tempfile, os

        with tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False) as f:
            f.write("# Weekly Report\n\nContent here.\n")
            tmp = f.name
        try:
            import_resp = {"code": 0, "data": {"ticket": "ticket_xyz"}}
            poll_resp = self._make_poll_resp(job_status=0, token="tok123", url="https://feishu.cn/docx/tok123")

            with patch("movietrace.feishu.sync.fetch_tenant_access_token", return_value="bearer"):
                with patch("movietrace.feishu.sync.upload_media_file", return_value="file_tok"):
                    with patch("movietrace.feishu.sync.request_json") as mock_rj:
                        mock_rj.side_effect = [import_resp, poll_resp]
                        with patch("movietrace.feishu.sync.time.sleep"):
                            result = sync_doc(tmp, "My Doc", "folder_abc",
                                              app_id="aid", app_secret="asec")

            self.assertEqual(result["doc_token"], "tok123")
            self.assertIn("tok123", result["doc_url"])
        finally:
            os.unlink(tmp)

    def test_polls_until_done(self):
        from movietrace.feishu.sync import sync_doc
        import tempfile, os

        with tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False) as f:
            f.write("# Content\n")
            tmp = f.name
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
            self.assertEqual(mock_rj.call_count, 4)  # 1 import + 3 polls
        finally:
            os.unlink(tmp)

    def test_raises_on_job_error(self):
        from movietrace.feishu.sync import sync_doc
        import tempfile, os

        with tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False) as f:
            f.write("# Content\n")
            tmp = f.name
        try:
            import_resp = {"code": 0, "data": {"ticket": "tck"}}
            error_resp = {"code": 0, "data": {"result": {"job_status": 3, "job_error_msg": "format not supported"}}}

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
            f.write("# Content\n")
            tmp = f.name
        try:
            perm_denied = {"code": 99991663, "msg": "no permission"}

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
