import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


class ConfigTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmpdir.name)

    def tearDown(self):
        self.tmpdir.cleanup()

    def _make_secrets(self, data: dict, perms: int = 0o600) -> Path:
        import json
        import os

        f = self.tmp_path / f"secrets_{len(list(self.tmp_path.glob('*.json')))}.json"
        f.write_text(json.dumps(data), encoding="utf-8")
        os.chmod(f, perms)
        return f

    def test_load_secrets_from_new_path(self):
        from movietrace.config import load_secrets

        data = {"tmdb": {"api_read_access_token": "test_token"}}
        f = self._make_secrets(data)

        result = load_secrets(f)
        self.assertEqual(result["tmdb"]["api_read_access_token"], "test_token")

    def test_load_secrets_file_not_found(self):
        from movietrace.config import load_secrets

        with self.assertRaises(RuntimeError):
            load_secrets(self.tmp_path / "nonexistent.json")

    def test_load_secrets_invalid_json(self):
        from movietrace.config import load_secrets

        f = self.tmp_path / "bad.json"
        f.write_text("not json")

        with self.assertRaises(RuntimeError):
            load_secrets(f)

    def test_load_secrets_falls_back_to_legacy(self):
        from movietrace.config import load_secrets, DEFAULT_SECRETS_PATH, LEGACY_SECRETS_PATH

        data = {"tmdb": {"api_read_access_token": "legacy_token"}}
        legacy = self._make_secrets(data)

        with patch("movietrace.config.DEFAULT_SECRETS_PATH", self.tmp_path / "nonexistent.json"):
            with patch("movietrace.config.LEGACY_SECRETS_PATH", legacy):
                result = load_secrets()
                self.assertEqual(result["tmdb"]["api_read_access_token"], "legacy_token")

    def test_load_secrets_invalid_default_json_falls_back_to_legacy(self):
        from movietrace.config import load_secrets

        default = self.tmp_path / "default_bad.json"
        default.write_text("not json", encoding="utf-8")
        legacy = self._make_secrets({"tmdb": {"api_read_access_token": "legacy_token"}})

        with patch("movietrace.config.DEFAULT_SECRETS_PATH", default):
            with patch("movietrace.config.LEGACY_SECRETS_PATH", legacy):
                result = load_secrets()

        self.assertEqual(result["tmdb"]["api_read_access_token"], "legacy_token")

    def test_load_secrets_explicit_invalid_json_does_not_fallback(self):
        from movietrace.config import load_secrets

        explicit = self.tmp_path / "explicit_bad.json"
        explicit.write_text("not json", encoding="utf-8")
        legacy = self._make_secrets({"tmdb": {"api_read_access_token": "legacy_token"}})

        with patch("movietrace.config.LEGACY_SECRETS_PATH", legacy):
            with self.assertRaises(RuntimeError):
                load_secrets(explicit)

    def test_get_secrets_path(self):
        from movietrace.config import get_secrets_path

        path = get_secrets_path()
        self.assertIn(".config", str(path))
        self.assertIn("movietrace", str(path))
        self.assertEqual(path.name, "secrets.json")


class ConfigPermissionsTest(unittest.TestCase):
    def setUp(self):
        import json
        import os

        self.tmpdir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmpdir.name)
        self.secrets_file = self.tmp_path / "secrets.json"
        self.secrets_file.write_text(json.dumps({"test": True}), encoding="utf-8")

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_warns_on_non_600_permissions(self):
        import os
        from movietrace.config import _check_permissions

        os.chmod(self.secrets_file, 0o644)
        with self.assertLogs("movietrace.config", level="WARNING") as log_capture:
            _check_permissions(self.secrets_file)

        self.assertTrue(
            any("600" in msg for msg in log_capture.output),
            f"No permission warning in: {log_capture.output}",
        )

    def test_no_warning_on_600_permissions(self):
        import os
        from movietrace.config import _check_permissions

        os.chmod(self.secrets_file, 0o600)
        with self.assertRaises(AssertionError):
            with self.assertLogs("movietrace.config", level="WARNING") as log_capture:
                _check_permissions(self.secrets_file)


class DeepMergeTest(unittest.TestCase):
    def test_merges_nested_dicts(self):
        from movietrace.config import _deep_merge

        base = {"feishu": {"app_id": "prod_id", "table": "tbl_prod"}}
        override = {"feishu": {"table": "tbl_test"}}
        result = _deep_merge(base, override)
        self.assertEqual(result["feishu"]["app_id"], "prod_id")   # kept
        self.assertEqual(result["feishu"]["table"], "tbl_test")   # overridden

    def test_adds_new_top_level_keys(self):
        from movietrace.config import _deep_merge

        base = {"tmdb": {"token": "x"}}
        override = {"trakt": {"client_id": "y"}}
        result = _deep_merge(base, override)
        self.assertIn("tmdb", result)
        self.assertIn("trakt", result)

    def test_replaces_scalar_values(self):
        from movietrace.config import _deep_merge

        base = {"key": "old"}
        override = {"key": "new"}
        result = _deep_merge(base, override)
        self.assertEqual(result["key"], "new")

    def test_does_not_mutate_base(self):
        from movietrace.config import _deep_merge

        base = {"feishu": {"app_id": "prod"}}
        override = {"feishu": {"app_id": "test"}}
        _deep_merge(base, override)
        self.assertEqual(base["feishu"]["app_id"], "prod")  # unchanged


class SmokeOverlayTest(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.tmpdir_obj = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self.tmpdir_obj.name)
        self.prod_file = self.tmpdir / "secrets.json"
        self.smoke_file = self.tmpdir / "secrets.smoke-test.json"

    def tearDown(self):
        self.tmpdir_obj.cleanup()

    def _write(self, path: Path, data: dict):
        import json
        path.write_text(json.dumps(data), encoding="utf-8")

    def test_no_overlay_when_env_not_set(self):
        from movietrace.config import _apply_smoke_overlay
        import os

        secrets = {"feishu": {"app_id": "prod"}}
        with patch.dict(os.environ, {}, clear=True):
            result = _apply_smoke_overlay(secrets)
        self.assertEqual(result["feishu"]["app_id"], "prod")

    @patch("movietrace.config.SMOKE_TEST_SECRETS_PATH")
    def test_warns_when_env_set_but_file_missing(self, mock_path):
        from movietrace.config import _apply_smoke_overlay
        import os

        mock_path.exists.return_value = False
        mock_path.__str__ = lambda s: "/fake/smoke-test.json"
        secrets = {"feishu": {"app_id": "prod"}}
        with patch.dict(os.environ, {"MOVIETRACE_SMOKE": "1"}):
            with self.assertLogs("movietrace.config", level="WARNING") as log_capture:
                result = _apply_smoke_overlay(secrets)
        self.assertIn("not found", log_capture.output[0])
        self.assertEqual(result["feishu"]["app_id"], "prod")  # unchanged

    def test_overrides_table_ids_when_env_set(self):
        from movietrace.config import _apply_smoke_overlay
        import os

        prod = {"feishu": {"app_id": "cli_abc", "base_app_token": "P6y3bM",
                            "discovery_table_id": "tbl84xx", "gap_table_id": "tbl1NNU"}}
        smoke = {"feishu": {"base_app_token": "WyMAbu",
                             "discovery_table_id": "tbl16QY", "gap_table_id": "tbleI8J"}}
        self._write(self.smoke_file, smoke)

        with patch("movietrace.config.SMOKE_TEST_SECRETS_PATH", self.smoke_file):
            with patch.dict(os.environ, {"MOVIETRACE_SMOKE": "1"}):
                result = _apply_smoke_overlay(prod)

        self.assertEqual(result["feishu"]["app_id"], "cli_abc")      # from prod
        self.assertEqual(result["feishu"]["base_app_token"], "WyMAbu")  # overridden
        self.assertEqual(result["feishu"]["discovery_table_id"], "tbl16QY")
        self.assertEqual(result["feishu"]["gap_table_id"], "tbleI8J")


class GetDbPathTest(unittest.TestCase):
    def test_returns_default_when_no_env(self):
        from movietrace.config import get_db_path, DEFAULT_DB_PATH
        import os
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(get_db_path(), DEFAULT_DB_PATH)

    def test_returns_smoke_when_env_set(self):
        from movietrace.config import get_db_path, SMOKE_DB_PATH
        import os
        with patch.dict(os.environ, {"MOVIETRACE_SMOKE": "1"}):
            self.assertEqual(get_db_path(), SMOKE_DB_PATH)

    def test_explicit_path_takes_precedence(self):
        from movietrace.config import get_db_path
        import os
        with patch.dict(os.environ, {"MOVIETRACE_SMOKE": "1"}):
            self.assertEqual(get_db_path("/custom/path.db"), "/custom/path.db")

    def test_explicit_path_without_env(self):
        from movietrace.config import get_db_path
        import os
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(get_db_path("/other.db"), "/other.db")

    def test_empty_string_returns_empty_string(self):
        from movietrace.config import get_db_path, DEFAULT_DB_PATH
        import os
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(get_db_path(""), "")

    def test_paths_are_different(self):
        from movietrace.config import DEFAULT_DB_PATH, SMOKE_DB_PATH
        self.assertNotEqual(DEFAULT_DB_PATH, SMOKE_DB_PATH)


if __name__ == "__main__":
    unittest.main()
