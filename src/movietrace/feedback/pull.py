"""Pull operator feedback from Feishu bitable tables (read-only).

Hot table: pulls all records, caller filters by discovery_date.
Gap table: full current snapshot.
Retries: 2 retries (3 total) with exponential backoff on HTTP errors.
"""
from __future__ import annotations

import json
import shutil
import time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from movietrace.feishu._http import OPEN_API_BASE, request_json, unwrap_text_field
from movietrace.feishu.baseline import fetch_tenant_access_token

TZ = ZoneInfo("Asia/Shanghai")


def _request_with_retry(method: str, url: str, *, token: str, payload: dict | None = None) -> dict:
    """request_json with 2 retries, exponential backoff 1 s / 2 s."""
    last_exc: Exception | None = None
    for attempt, wait in enumerate([0, 1, 2]):
        if wait:
            time.sleep(wait)
        try:
            return request_json(method, url, token=token, payload=payload)
        except Exception as exc:
            last_exc = exc
    raise RuntimeError(f"Feishu request failed after 3 attempts: {last_exc}") from last_exc


def _list_records(token: str, app_token: str, table_id: str) -> list[dict]:
    """Fetch all records from a table via paginated search."""
    url = f"{OPEN_API_BASE}/bitable/v1/apps/{app_token}/tables/{table_id}/records/search"
    records: list[dict] = []
    page_token = ""

    while True:
        payload: dict = {"page_size": 500}
        if page_token:
            payload["page_token"] = page_token

        resp = _request_with_retry("POST", url, token=token, payload=payload)
        if resp.get("code") != 0:
            raise RuntimeError(f"list records failed: {resp}")

        data = resp.get("data", {})
        records.extend(data.get("items", []))

        if not data.get("has_more"):
            break
        page_token = data.get("page_token", "")
        if not page_token:
            break

    return records


def _unwrap_select(value) -> str:
    """Unwrap a Feishu select field (may be str or list)."""
    if isinstance(value, list):
        return value[0] if value else ""
    return str(value) if value is not None else ""


def _unwrap_user(value) -> str:
    """Unwrap a Feishu user field to open_id string."""
    if isinstance(value, list) and value:
        return str(value[0].get("id", "")) if isinstance(value[0], dict) else str(value[0])
    if isinstance(value, dict):
        return str(value.get("id", ""))
    return str(value) if value is not None else ""


def _epoch_ms_to_date(epoch_ms) -> str:
    """Convert Feishu epoch-ms date field to 'YYYY-MM-DD' string."""
    if epoch_ms is None:
        return ""
    try:
        return datetime.fromtimestamp(int(epoch_ms) / 1000, tz=TZ).strftime("%Y-%m-%d")
    except (ValueError, TypeError, OSError):
        return ""


def pull_hot_table(
    token: str,
    app_token: str,
    table_id: str,
    days: int = 7,
) -> list[dict]:
    """Pull hot-table records for the last `days` days.

    Fetches all records then filters client-side by discovery_date.
    Returns list of normalized record dicts.
    """
    cutoff = (datetime.now(TZ) - timedelta(days=days)).strftime("%Y-%m-%d")
    raw = _list_records(token, app_token, table_id)

    result: list[dict] = []
    for item in raw:
        fields = item.get("fields", {})
        # Feishu search API returns fields by Chinese name, not field ID
        discovery_date = _epoch_ms_to_date(fields.get("发现日期"))
        if discovery_date and discovery_date < cutoff:
            continue

        content_update_id = unwrap_text_field(fields.get("content_update_id"))
        title = unwrap_text_field(fields.get("标题"))
        priority = _unwrap_select(fields.get("优先级"))
        hot_score_raw = fields.get("hot_score")
        try:
            hot_score = float(hot_score_raw) if hot_score_raw is not None else None
        except (ValueError, TypeError):
            hot_score = None
        tmdb_id = unwrap_text_field(fields.get("TMDb ID"))
        operator_status = _unwrap_select(fields.get("运营状态"))
        operator_note = unwrap_text_field(fields.get("运营备注"))
        vendor_status = _unwrap_select(fields.get("供应商状态"))
        assignee = _unwrap_user(fields.get("负责人"))

        result.append({
            "record_id": item.get("record_id", ""),
            "content_update_id": content_update_id,
            "title": title,
            "discovery_date": discovery_date,
            "priority": priority,
            "hot_score": hot_score,
            "tmdb_id": tmdb_id,
            "operator_status": operator_status,
            "operator_note": operator_note,
            "vendor_status": vendor_status,
            "assignee": assignee,
        })

    return result


def pull_gap_table(
    token: str,
    app_token: str,
    table_id: str,
) -> list[dict]:
    """Pull full gap-table snapshot. Returns list of normalized record dicts."""
    raw = _list_records(token, app_token, table_id)

    result: list[dict] = []
    for item in raw:
        fields = item.get("fields", {})
        tmdb_id = unwrap_text_field(fields.get("TMDb ID", ""))
        name = unwrap_text_field(fields.get("剧集名", ""))
        hot_score_raw = fields.get("hot_score")
        try:
            hot_score = float(hot_score_raw) if hot_score_raw is not None else None
        except (ValueError, TypeError):
            hot_score = None
        gap_count_raw = fields.get("缺口数")
        try:
            gap_count = int(gap_count_raw) if gap_count_raw is not None else None
        except (ValueError, TypeError):
            gap_count = None
        gap_seasons = unwrap_text_field(fields.get("缺口季", ""))
        operator_status = _unwrap_select(fields.get("运营状态", ""))
        operator_note = unwrap_text_field(fields.get("备注", ""))
        assignee = _unwrap_user(fields.get("负责人", ""))

        result.append({
            "record_id": item.get("record_id", ""),
            "tmdb_id": tmdb_id,
            "name": name,
            "hot_score": hot_score,
            "gap_count": gap_count,
            "gap_seasons": gap_seasons,
            "operator_status": operator_status,
            "operator_note": operator_note,
            "assignee": assignee,
        })

    return result


def pull_all(
    *,
    app_id: str,
    app_secret: str,
    app_token: str,
    hot_table_id: str,
    gap_table_id: str,
    days: int = 7,
    output_dir: str | Path = "reports/feedback",
    dry_run: bool = False,
) -> dict:
    """Pull both tables, save to JSON, update latest symlink/copy.

    Returns the pull result dict (same structure saved to disk).
    """
    pulled_at = datetime.now(TZ).strftime("%Y-%m-%dT%H:%M:%S+08:00")

    print(f"Authenticating with Feishu...", end=" ", flush=True)
    token = fetch_tenant_access_token(app_id, app_secret)
    print("OK")

    print(f"Pulling hot table ({hot_table_id}, last {days} days)...", end=" ", flush=True)
    hot_records = pull_hot_table(token, app_token, hot_table_id, days=days)
    print(f"{len(hot_records)} records")

    print(f"Pulling gap table ({gap_table_id}, full snapshot)...", end=" ", flush=True)
    gap_records = pull_gap_table(token, app_token, gap_table_id)
    print(f"{len(gap_records)} records")

    result = {
        "pulled_at": pulled_at,
        "hot_table": {
            "table_id": hot_table_id,
            "range_days": days,
            "records": hot_records,
        },
        "gap_table": {
            "table_id": gap_table_id,
            "records": gap_records,
        },
    }

    if dry_run:
        print("\n[DRY-RUN] 不写文件，仅打印摘要：")
        print(f"  hot_table: {len(hot_records)} records (last {days} days)")
        print(f"  gap_table: {len(gap_records)} records")
        return result

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(TZ).strftime("%Y-%m-%d_%H%M")
    out_path = out_dir / f"feishu_pull_{ts}.json"
    latest_path = out_dir / "feishu_pull_latest.json"

    out_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    shutil.copy2(out_path, latest_path)

    print(f"\n已写入: {out_path}")
    print(f"已更新: {latest_path}")
    return result
