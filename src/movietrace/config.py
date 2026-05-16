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


def get_secrets_path() -> Path:
    """Return the preferred secrets path (new location)."""
    return DEFAULT_SECRETS_PATH


def load_secrets(path: str | Path | None = None) -> dict:
    """Load secrets JSON. New path (~/.config/movietrace/secrets.json) preferred,
    falls back to legacy path (/tmp) with deprecation warning.

    Raises RuntimeError when no valid secrets file can be loaded.
    """
    if path:
        resolved = Path(path)
    else:
        resolved = DEFAULT_SECRETS_PATH

    if resolved.exists():
        _check_permissions(resolved)
        try:
            return json.loads(resolved.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            if path is None and LEGACY_SECRETS_PATH.exists():
                logger.warning("Secrets file %s is invalid JSON, trying legacy path", resolved)
                _check_permissions(LEGACY_SECRETS_PATH)
                try:
                    return json.loads(LEGACY_SECRETS_PATH.read_text(encoding="utf-8"))
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
            return json.loads(LEGACY_SECRETS_PATH.read_text(encoding="utf-8"))
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
