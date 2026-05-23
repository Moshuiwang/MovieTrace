from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

_HB_PATH = str(Path(__file__).resolve().parents[3] / "data" / "pipeline_heartbeat.json")
_TZ_CN = timezone(timedelta(hours=8))


def ping(step: str, detail: str = "", *, hb_path: str = _HB_PATH) -> None:
    """Write a best-effort pipeline heartbeat."""
    payload = {
        "step": step,
        "detail": detail,
        "ts": datetime.now(_TZ_CN).isoformat(timespec="seconds"),
        "pid": os.getpid(),
        "status": "running",
    }
    try:
        with open(hb_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)
    except OSError:
        pass


def done(*, hb_path: str = _HB_PATH) -> None:
    """Mark the current pipeline heartbeat as done."""
    try:
        with open(hb_path, "r+", encoding="utf-8") as f:
            data = json.load(f)
            data["status"] = "done"
            f.seek(0)
            json.dump(data, f, ensure_ascii=False)
            f.truncate()
    except (OSError, json.JSONDecodeError):
        pass
