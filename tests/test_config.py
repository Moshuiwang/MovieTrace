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

        result = load_secrets(self.tmp_path / "nonexistent.json")
        self.assertEqual(result, {})

    def test_load_secrets_invalid_json(self):
        from movietrace.config import load_secrets

        f = self.tmp_path / "bad.json"
        f.write_text("not json")

        result = load_secrets(f)
        self.assertEqual(result, {})

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
            result = load_secrets(explicit)

        self.assertEqual(result, {})

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


if __name__ == "__main__":
    unittest.main()
