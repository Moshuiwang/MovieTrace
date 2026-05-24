"""Tests for feishu/_http.py shared HTTP helpers."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


class TestBuildMultipartBody(unittest.TestCase):
    def test_text_field_appears_in_body(self):
        from movietrace.feishu._http import build_multipart_body
        body, boundary = build_multipart_body({"file_name": "report.md"})
        text = body.decode("utf-8")
        self.assertIn(f"--{boundary}", text)
        self.assertIn('name="file_name"', text)
        self.assertIn("report.md", text)

    def test_file_field_uses_filename_and_content_type(self):
        from movietrace.feishu._http import build_multipart_body
        file_data = b"hello world"
        body, boundary = build_multipart_body({
            "file": (file_data, "test.md", "application/octet-stream"),
        })
        text = body.decode("utf-8", errors="replace")
        self.assertIn('filename="test.md"', text)
        self.assertIn("application/octet-stream", text)

    def test_body_ends_with_closing_boundary(self):
        from movietrace.feishu._http import build_multipart_body
        body, boundary = build_multipart_body({"k": "v"})
        self.assertTrue(body.endswith(f"--{boundary}--\r\n".encode()))

    def test_boundary_is_unique_per_call(self):
        from movietrace.feishu._http import build_multipart_body
        _, b1 = build_multipart_body({"k": "v"})
        _, b2 = build_multipart_body({"k": "v"})
        self.assertNotEqual(b1, b2)


class TestUnwrapTextField(unittest.TestCase):
    def test_plain_string_returned_as_is(self):
        from movietrace.feishu._http import unwrap_text_field
        self.assertEqual(unwrap_text_field("hello"), "hello")

    def test_list_of_segments_joined(self):
        from movietrace.feishu._http import unwrap_text_field
        segments = [{"text": "foo", "type": "text"}, {"text": "bar", "type": "text"}]
        self.assertEqual(unwrap_text_field(segments), "foobar")

    def test_none_returns_empty_string(self):
        from movietrace.feishu._http import unwrap_text_field
        self.assertEqual(unwrap_text_field(None), "")

    def test_empty_list_returns_empty_string(self):
        from movietrace.feishu._http import unwrap_text_field
        self.assertEqual(unwrap_text_field([]), "")

    def test_segment_missing_text_key_contributes_empty(self):
        from movietrace.feishu._http import unwrap_text_field
        self.assertEqual(unwrap_text_field([{"type": "mention"}]), "")


class TestRequestJson(unittest.TestCase):
    def _patch_policy(self, status, body_str):
        return patch(
            "movietrace.feishu._http.request_with_policy",
            return_value=(status, body_str.encode("utf-8"), {}),
        )

    def test_ok_response_returns_parsed_dict(self):
        from movietrace.feishu._http import request_json
        payload = {"code": 0, "data": {"id": "abc"}}
        with self._patch_policy(200, json.dumps(payload)):
            result = request_json("GET", "https://example.com/api", token="tok")
        self.assertEqual(result["code"], 0)
        self.assertEqual(result["data"]["id"], "abc")

    def test_http_error_raises_runtime_error(self):
        from movietrace.feishu._http import request_json
        with self._patch_policy(403, '{"msg":"forbidden"}'):
            with self.assertRaises(RuntimeError) as ctx:
                request_json("GET", "https://example.com/api", token="tok")
        self.assertIn("403", str(ctx.exception))

    def test_access_token_masked_in_error_message(self):
        """access_token must not leak in RuntimeError messages."""
        from movietrace.feishu._http import request_json
        raw = '{"access_token":"SECRET_TOKEN_VALUE","msg":"bad"}'
        with self._patch_policy(401, raw):
            with self.assertRaises(RuntimeError) as ctx:
                request_json("POST", "https://example.com/api", token="tok")
        self.assertNotIn("SECRET_TOKEN_VALUE", str(ctx.exception))
        self.assertIn("***", str(ctx.exception))

    def test_no_token_omits_authorization_header(self):
        """When token is None, Authorization header must not be included."""
        from movietrace.feishu._http import request_json
        with patch("movietrace.feishu._http.request_with_policy",
                   return_value=(200, b'{"code":0}', {})) as mock_req:
            request_json("GET", "https://example.com/api", token=None)
        _, kwargs = mock_req.call_args
        headers = mock_req.call_args[1].get("headers") or mock_req.call_args[0][2]
        self.assertNotIn("Authorization", headers)


class TestBatchOperations(unittest.TestCase):
    def _make_ok_response(self):
        return (200, json.dumps({"code": 0}).encode(), {})

    def test_batch_create_raises_on_nonzero_code(self):
        from movietrace.feishu._http import batch_create_records
        err_resp = (200, json.dumps({"code": 1254711, "msg": "quota exceeded"}).encode(), {})
        with patch("movietrace.feishu._http.request_with_policy", return_value=err_resp):
            with self.assertRaises(RuntimeError) as ctx:
                batch_create_records("tok", "app", "tbl", [{"fields": {"k": "v"}}])
        self.assertIn("batch create", str(ctx.exception))

    def test_batch_update_chunks_at_500(self):
        """batch_update_records must call request_with_policy twice for 501 updates."""
        from movietrace.feishu._http import batch_update_records
        updates = [{"record_id": f"r{i}", "fields": {}} for i in range(501)]
        with patch("movietrace.feishu._http.request_with_policy",
                   return_value=self._make_ok_response()) as mock_req:
            batch_update_records("tok", "app", "tbl", updates)
        self.assertEqual(mock_req.call_count, 2)

    def test_batch_delete_chunks_at_500(self):
        """batch_delete_records must call request_with_policy twice for 501 record IDs."""
        from movietrace.feishu._http import batch_delete_records
        record_ids = [f"r{i}" for i in range(501)]
        with patch("movietrace.feishu._http.request_with_policy",
                   return_value=self._make_ok_response()) as mock_req:
            batch_delete_records("tok", "app", "tbl", record_ids)
        self.assertEqual(mock_req.call_count, 2)

    def test_batch_update_raises_on_nonzero_code(self):
        from movietrace.feishu._http import batch_update_records
        err_resp = (200, json.dumps({"code": 500, "msg": "err"}).encode(), {})
        with patch("movietrace.feishu._http.request_with_policy", return_value=err_resp):
            with self.assertRaises(RuntimeError) as ctx:
                batch_update_records("tok", "app", "tbl", [{"record_id": "r1", "fields": {}}])
        self.assertIn("batch update", str(ctx.exception))

    def test_batch_delete_raises_on_nonzero_code(self):
        from movietrace.feishu._http import batch_delete_records
        err_resp = (200, json.dumps({"code": 500, "msg": "err"}).encode(), {})
        with patch("movietrace.feishu._http.request_with_policy", return_value=err_resp):
            with self.assertRaises(RuntimeError) as ctx:
                batch_delete_records("tok", "app", "tbl", ["r1"])
        self.assertIn("batch delete", str(ctx.exception))


class TestUploadMediaFile(unittest.TestCase):
    def _patch_policy(self, status, body_dict):
        return patch(
            "movietrace.feishu._http.request_with_policy",
            return_value=(status, json.dumps(body_dict).encode(), {}),
        )

    def test_returns_file_token_on_success(self):
        from movietrace.feishu._http import upload_media_file
        ok_body = {"code": 0, "data": {"file_token": "ftkn_abc123"}}
        with self._patch_policy(200, ok_body):
            token = upload_media_file("tok", "report.md", b"content")
        self.assertEqual(token, "ftkn_abc123")

    def test_permission_denied_code_raises_with_scope_hint(self):
        """Error codes 99991663/99991661/1061045 must mention 'drive:drive' scope."""
        from movietrace.feishu._http import upload_media_file
        perm_body = {"code": 99991663, "msg": "permission denied"}
        with self._patch_policy(200, perm_body):
            with self.assertRaises(RuntimeError) as ctx:
                upload_media_file("tok", "f.md", b"x")
        self.assertIn("drive:drive", str(ctx.exception))

    def test_http_error_raises_with_status_code(self):
        from movietrace.feishu._http import upload_media_file
        with self._patch_policy(403, {}):
            with self.assertRaises(RuntimeError) as ctx:
                upload_media_file("tok", "f.md", b"x")
        self.assertIn("403", str(ctx.exception))

    def test_missing_file_token_raises(self):
        from movietrace.feishu._http import upload_media_file
        no_token_body = {"code": 0, "data": {}}
        with self._patch_policy(200, no_token_body):
            with self.assertRaises(RuntimeError) as ctx:
                upload_media_file("tok", "f.md", b"x")
        self.assertIn("file_token", str(ctx.exception))

    def test_access_token_masked_in_upload_error(self):
        from movietrace.feishu._http import upload_media_file
        raw_body = '{"access_token":"LEAK_ME","msg":"err"}'.encode()
        with patch("movietrace.feishu._http.request_with_policy",
                   return_value=(400, raw_body, {})):
            with self.assertRaises(RuntimeError) as ctx:
                upload_media_file("tok", "f.md", b"x")
        self.assertNotIn("LEAK_ME", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
