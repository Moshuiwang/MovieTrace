from __future__ import annotations

import json
import logging
import os
import stat
from pathlib import Path

logger = logging.getLogger("movietrace.config")

DEFAULT_SECRETS_DIR = Path.home() / ".config" / "movietrace"
DEFAULT_SECRETS_PATH = DEFAULT_SECRETS_DIR / "secrets.json"
LEGACY_SECRETS_PATH = Path("/tmp/movietrace_phase0_secrets.json")
SMOKE_TEST_SECRETS_PATH = DEFAULT_SECRETS_DIR / "secrets.smoke-test.json"

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = str(_PROJECT_ROOT / "data" / "movietrace.db")
SMOKE_DB_PATH = str(_PROJECT_ROOT / "data" / "movietrace_smoke.db")


def get_db_path(explicit: str | None = None) -> str:
    """Resolve the database path.

    When MOVIETRACE_SMOKE=1, defaults to the smoke-test database; otherwise
    the production database. An explicit path (e.g. from --db CLI flag) always
    takes precedence.
    """
    if explicit is not None:
        return explicit
    if os.environ.get("MOVIETRACE_SMOKE") == "1":
        return SMOKE_DB_PATH
    return DEFAULT_DB_PATH


def get_secrets_path() -> Path:
    """Return the preferred secrets path (new location)."""
    return DEFAULT_SECRETS_PATH


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge *override* into *base*. Dicts are merged; scalars/lists replaced."""
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _apply_smoke_overlay(secrets: dict) -> dict:
    """When MOVIETRACE_SMOKE=1, deep-merge secrets.smoke-test.json on top."""
    if os.environ.get("MOVIETRACE_SMOKE") != "1":
        return secrets
    if not SMOKE_TEST_SECRETS_PATH.exists():
        logger.warning(
            "MOVIETRACE_SMOKE=1 but %s not found, using production secrets",
            SMOKE_TEST_SECRETS_PATH,
        )
        return secrets
    try:
        overlay = json.loads(SMOKE_TEST_SECRETS_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        logger.warning(
            "Smoke test secrets file %s is invalid JSON, using production secrets",
            SMOKE_TEST_SECRETS_PATH,
        )
        return secrets
    return _deep_merge(secrets, overlay)


def load_secrets(path: str | Path | None = None) -> dict:
    """Load secrets JSON. New path (~/.config/movietrace/secrets.json) preferred,
    falls back to legacy path (/tmp) with deprecation warning.

    When MOVIETRACE_SMOKE=1, additionally loads secrets.smoke-test.json and
    deep-merges it on top (overriding table IDs for the smoke-test Feishu base).

    Raises RuntimeError when no valid secrets file can be loaded.
    """
    if path:
        resolved = Path(path)
    else:
        resolved = DEFAULT_SECRETS_PATH

    if resolved.exists():
        _check_permissions(resolved)
        try:
            return _apply_smoke_overlay(json.loads(resolved.read_text(encoding="utf-8")))
        except json.JSONDecodeError as exc:
            if path is None and LEGACY_SECRETS_PATH.exists():
                logger.warning("Secrets file %s is invalid JSON, trying legacy path", resolved)
                _check_permissions(LEGACY_SECRETS_PATH)
                try:
                    return _apply_smoke_overlay(json.loads(LEGACY_SECRETS_PATH.read_text(encoding="utf-8")))
                except json.JSONDecodeError:
                    raise RuntimeError(
                        f"Both secrets files contain invalid JSON: "
                        f"{resolved} and {LEGACY_SECRETS_PATH}"
                    ) from exc
            raise RuntimeError(f"Secrets file {resolved} is invalid JSON") from exc

    if path is None and LEGACY_SECRETS_PATH.exists():
        logger.warning(
            "Secrets at %s not found, falling back to legacy path %s — "
            "please migrate to %s",
            DEFAULT_SECRETS_PATH, LEGACY_SECRETS_PATH, DEFAULT_SECRETS_PATH,
        )
        _check_permissions(LEGACY_SECRETS_PATH)
        try:
            return _apply_smoke_overlay(json.loads(LEGACY_SECRETS_PATH.read_text(encoding="utf-8")))
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"Legacy secrets file {LEGACY_SECRETS_PATH} is invalid JSON"
            ) from exc

    raise RuntimeError(
        f"No secrets file found at {resolved}. "
        "Create one with: mkdir -p ~/.config/movietrace && "
        "echo '{\"tmdb\":{\"api_read_access_token\":\"...\"}}' > ~/.config/movietrace/secrets.json && "
        "chmod 600 ~/.config/movietrace/secrets.json"
    )


def _check_permissions(path: Path) -> None:
    """Warn if secrets file permissions are not 0600."""
    try:
        mode = path.stat().st_mode
        perms = mode & 0o777
        if perms != 0o600:
            logger.warning(
                "Secrets file %s has permissions %o, expected 600 — consider: chmod 600 %s",
                path, perms, path,
            )
    except OSError:
        pass
