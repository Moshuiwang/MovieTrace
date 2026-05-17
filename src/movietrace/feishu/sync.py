"""Feishu bitable sync — record upsert via REST API, keyed by field ID.

Bitable operations use the app credentials from secrets.json (same as baseline.py),
NOT lark-cli bot identity, to avoid cross-app permission issues.
Doc sync uses the Feishu docx v1 REST API (POST /open-apis/docx/v1/documents).

Table and fields are pre-created via Feishu UI/API; this module does NOT auto-create.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

UTC = timezone.utc

from movietrace.feishu.baseline import fetch_tenant_access_token
import time

from movietrace.feishu._http import (
    OPEN_API_BASE,
    request_json,
    batch_create_records,
    batch_update_records,
    unwrap_text_field,
    upload_media_file,
)

TZ = ZoneInfo("Asia/Shanghai")

# ── REST API helpers ──────────────────────────────────────────────────────


def _to_epoch_ms(dt_str: str, tz=None) -> int | None:
    """Convert 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS' to Feishu epoch ms.

    tz defaults to CST (Asia/Shanghai). Pass UTC for DB-stored UTC timestamps.
    """
    if not dt_str:
        return None
    try:
        fmt = "%Y-%m-%d %H:%M:%S" if len(dt_str) > 10 else "%Y-%m-%d"
        used_tz = tz if tz is not None else TZ
        return int(datetime.strptime(dt_str[:19], fmt).replace(tzinfo=used_tz).timestamp() * 1000)
    except (ValueError, TypeError):
        return None


# ── Record operations ─────────────────────────────────────────────────────

def _list_records_for_date(
    token: str, app_token: str, table_id: str, run_date: str
) -> dict[str, str]:
    """Fetch all records for run_date. Returns {snapshot_key: record_id}."""
    url = f"{OPEN_API_BASE}/bitable/v1/apps/{app_token}/tables/{table_id}/records/search"
    lookup: dict[str, str] = {}
    page_token = ""

    while True:
        payload: dict = {
            "filter": {
                "conjunction": "and",
                "conditions": [
                    {
                        "field_name": "同步批次",  # text field; 发现日期(type=5) doesn't accept date strings in filter
                        "operator": "is",
                        "value": [run_date],
                    }
                ],
            },
            "page_size": 500,
        }
        if page_token:
            payload["page_token"] = page_token

        resp = request_json("POST", url, token=token, payload=payload)
        if resp.get("code") != 0:
            raise RuntimeError(f"list records for date failed: {resp}")

        data = resp.get("data", {})
        for item in data.get("items", []):
            fields = item.get("fields", {})
            # API may return rich-text segments for text fields
            cid_val = unwrap_text_field(fields.get("content_update_id", ""))
            record_id = item.get("record_id", "")
            if cid_val and record_id:
                lookup[cid_val] = record_id

        if not data.get("has_more"):
            break
        page_token = data.get("page_token", "")
        if not page_token:
            break

    return lookup


# ── Main sync function ────────────────────────────────────────────────────

def sync_table(
    json_path: str,
    run_date: str,
    app_id: str,
    app_secret: str,
    app_token: str,
    table_id: str,
    *,
    dry_run: bool = False,
) -> dict:
    """Sync latest.json records to a Feishu bitable by field_id.

    Table and fields must already exist (pre-created via UI or setup scripts).
    Unique key: run_date + content_update_id.

    Returns stats dict with keys: total, created, updated, errors.
    """
    path = Path(json_path)
    with open(path) as f:
        records = json.load(f)

    if not isinstance(records, list):
        raise ValueError(f"Expected JSON array, got {type(records).__name__}")

    print(f"读取 {len(records)} 条记录 from {json_path}")
    print(f"运行日期: {run_date}")
    print(f"Table ID:  {table_id}")

    if dry_run:
        print(f"\n[DRY-RUN] 将写入 {len(records)} 条记录 to table_id={table_id}")
        for i, rec in enumerate(records[:5]):
            cid = rec.get("content_update_id", "?")
            title = str(rec.get("title", "?"))[:50]
            print(f"  [{i+1}] {cid} | {title}")
        if len(records) > 5:
            print(f"  ... 以及 {len(records)-5} 条更多")
        return {"total": len(records), "created": 0, "updated": 0, "errors": 0, "dry_run": True}

    # 1. Get token
    print("获取飞书 token...")
    token = fetch_tenant_access_token(app_id, app_secret)

    # 2. Fetch existing records for this date
    print(f"加载 {run_date} 已有记录...")
    existing_lookup = _list_records_for_date(token, app_token, table_id, run_date)
    print(f"  已有记录: {len(existing_lookup)} 条")

    # 3. Build records, separate creates from updates
    print("同步记录...")
    stats = {"total": len(records), "created": 0, "updated": 0, "errors": 0}
    now_ts = int(datetime.now(TZ).timestamp() * 1000)

    new_discovery_count = 0
    new_season_count = 0
    p0_count = 0
    p1_count = 0
    p2_count = 0
    source_statuses: dict[str, str] = {}

    to_create: list[dict] = []
    to_update: list[tuple[str, dict]] = []  # (record_id, fields)

    for i, rec in enumerate(records):
        try:
            cid = rec.get("content_update_id", "")
            snapshot_key = f"{run_date}|{cid}"

            source_status = rec.get("source_data_status")
            source_status_str = ""
            if source_status:
                parts = []
                for src, info in source_status.items():
                    st = info.get("status", "?")
                    parts.append(f"{src}={st}")
                    source_statuses[src] = st
                source_status_str = ", ".join(parts)

            # event_written_at_utc / created_at are both stored as UTC in the DB
            detected_at = _to_epoch_ms(
                rec.get("event_written_at_utc") or rec.get("created_at", ""),
                tz=UTC,
            )
            fields: dict = {
                "发现日期":          _to_epoch_ms(run_date),
                "content_update_id": snapshot_key,
                "标题":             str(rec.get("title", "")),
                "类型":             _derive_content_type(rec),
                "更新类型":          str(rec.get("update_type", "")),
                "优先级":            str(rec.get("priority", "")),
                "hot_score":        float(rec.get("hot_score") or 0),
                "季号":             int(rec.get("season") or 0),
                "TMDb ID":          str(rec.get("tmdb_id") or rec.get("tmdb_tv_id") or ""),
                "A库最新季":         f"S{rec['upstream_max_season']}" if rec.get("upstream_max_season") is not None else "无",
                "是否低置信度":        "是" if rec.get("match_confidence_low") else "否",
                "数据源状态":         source_status_str,
                "同步时间":          now_ts,
                "同步批次":          run_date,
            }
            if detected_at is not None:
                fields["检测时间"] = detected_at

            ut = rec.get("update_type", "")
            if ut == "new_discovery":
                new_discovery_count += 1
            elif ut == "new_season":
                new_season_count += 1

            pri = rec.get("priority", "")
            if pri == "P0":
                p0_count += 1
            elif pri == "P1":
                p1_count += 1
            elif pri == "P2":
                p2_count += 1

            if snapshot_key in existing_lookup:
                to_update.append((existing_lookup[snapshot_key], fields))
                stats["updated"] += 1
            else:
                fields["运营状态"] = "待看"
                fields["供应商状态"] = "未提交"
                # 负责人 omitted: user field cannot accept empty string
                to_create.append({"fields": fields})
                stats["created"] += 1

            if (i + 1) % 10 == 0 or (i + 1) == len(records):
                print(f"  进度: {i+1}/{len(records)} (created={stats['created']}, updated={stats['updated']}, errors={stats['errors']})")

        except Exception as e:
            stats["errors"] += 1
            print(f"  ERROR [{i+1}] {rec.get('content_update_id', '?')}: {e}")

    # 4. Batch create new records (100 per batch for safety)
    batch_size = 100
    for start in range(0, len(to_create), batch_size):
        batch = to_create[start:start + batch_size]
        try:
            batch_create_records(token, app_token, table_id, batch)
        except Exception as e:
            print(f"  ERROR batch create [{start}:{start+len(batch)}]: {e}")
            stats["errors"] += len(batch)
            stats["created"] -= len(batch)

    # 5. Batch update existing records (500 per call via _http)
    if to_update:
        updates = [{"record_id": rid, "fields": fields} for rid, fields in to_update]
        try:
            batch_update_records(token, app_token, table_id, updates)
        except Exception as e:
            print(f"  ERROR batch update {len(to_update)} records: {e}")
            stats["errors"] += len(to_update)
            stats["updated"] -= len(to_update)

    stats["new_discovery"] = new_discovery_count
    stats["new_season"] = new_season_count
    stats["p0_count"] = p0_count
    stats["p1_count"] = p1_count
    stats["p2_count"] = p2_count
    stats["source_status"] = ", ".join(f"{k}={v}" for k, v in source_statuses.items())

    return stats


def _derive_content_type(rec: dict) -> str:
    if ct := rec.get("content_type"):
        return ct
    if rec.get("update_type") == "new_season":
        return "tv"
    cid = rec.get("content_update_id", "")
    if isinstance(cid, str):
        if ":movie:" in cid:
            return "movie"
        if ":tv:" in cid:
            return "tv"
    return "unknown"


# ── Doc sync (via Feishu drive/v1/import_task) ───────────────────────────────

_IMPORT_POLL_DELAYS = [1, 2, 4, 8, 16, 30, 30, 30, 30, 30]  # seconds; hard timeout ~155s
_IMPORT_TIMEOUT_SECONDS = 300  # 5-minute hard cap


def sync_doc(
    md_path: str,
    title: str,
    folder_token: str = "",
    *,
    app_id: str = "",
    app_secret: str = "",
    dry_run: bool = False,
    target_type: str = "auto",
) -> dict:
    """Import a Markdown file as a Feishu docx via drive/v1/import_task or wiki/v2 API.

    Two modes:
      - drive (folder): via drive/v1/import_task (current behavior)
      - wiki: via wiki/v2/spaces/{space_id}/docs/import_docx
      - auto: detect based on token format

    App needs 'drive:drive' scope.  Permission errors (99991661/99991663/1061045)
    raise RuntimeError with an explicit console instruction.

    Returns: {"doc_url": str, "doc_token": str}
    """
    path = Path(md_path)
    content = path.read_text(encoding="utf-8")
    file_data = content.encode("utf-8")

    if dry_run:
        print(f"[DRY-RUN] 将导入飞书文档: {title}")
        print(f"[DRY-RUN] 文件: {md_path} ({len(file_data)} bytes)")
        return {"doc_url": "", "doc_token": "", "dry_run": True}

    if not app_id or not app_secret:
        raise RuntimeError("sync_doc requires app_id and app_secret")
    if not folder_token:
        raise RuntimeError("sync_doc requires folder_token (the Feishu folder/space to import into)")

    token = fetch_tenant_access_token(app_id, app_secret)

    # Auto-detect target type based on token format
    if target_type == "auto":
        target_type = "wiki" if len(folder_token) == 28 else "drive"

    if target_type == "wiki":
        return _sync_doc_to_wiki(token, md_path, title, folder_token, file_data)
    else:
        return _sync_doc_to_drive(token, md_path, title, folder_token, file_data)



def _sync_doc_to_drive(
    token: str, md_path: str, title: str, folder_token: str, file_data: bytes
) -> dict:
    """Import via drive/v1/import_task (文件夹导入)."""
    path = Path(md_path)
    file_name = path.name if path.name.endswith(".md") else f"{title}.md"
    print(f"上传文件 {file_name} ({len(file_data)} bytes)...")
    file_token = upload_media_file(token, file_name, file_data)

    print("创建导入任务...")
    import_url = f"{OPEN_API_BASE}/drive/v1/import_tasks"
    import_payload: dict = {
        "file_extension": "md",
        "file_token": file_token,
        "type": "docx",
        "file_name": title,
        "point": {
            "mount_type": 1,
            "mount_key": folder_token or "",
        },
    }
    import_resp = request_json("POST", import_url, token=token, payload=import_payload)
    if import_resp.get("code") != 0:
        code = import_resp.get("code")
        msg = import_resp.get("msg", "")
        if code in (99991663, 99991661, 1061045):
            raise RuntimeError(
                f"Feishu import task permission denied (code={code}): {msg}. "
                "Grant the app 'drive:drive' scope in the Feishu console."
            )
        raise RuntimeError(f"Feishu import_task create failed (code={code}): {msg}")

    ticket = import_resp.get("data", {}).get("ticket", "")
    if not ticket:
        raise RuntimeError(f"Feishu import_task returned no ticket: {import_resp}")
    print(f"导入任务已创建，ticket={ticket}")

    poll_url = f"{OPEN_API_BASE}/drive/v1/import_tasks/{ticket}"
    deadline = time.monotonic() + _IMPORT_TIMEOUT_SECONDS

    for delay in _IMPORT_POLL_DELAYS:
        time.sleep(delay)
        if time.monotonic() > deadline:
            break

        poll_resp = request_json("GET", poll_url, token=token)
        if poll_resp.get("code") != 0:
            code = poll_resp.get("code")
            msg = poll_resp.get("msg", "")
            raise RuntimeError(f"Feishu import_task poll failed (code={code}): {msg}")

        result = poll_resp.get("data", {}).get("result", {})
        job_status = result.get("job_status", -1)

        if job_status == 0:
            doc_token = result.get("token", "")
            doc_url = result.get("url", "") or f"https://bytedance.feishu.cn/docx/{doc_token}"
            print(f"导入完成: {doc_url}")
            return {"doc_url": doc_url, "doc_token": doc_token}

        if job_status >= 3:
            job_error_msg = result.get("job_error_msg", "")
            raise RuntimeError(
                f"Feishu import_task failed (job_status={job_status}): {job_error_msg}"
            )

        print(f"  导入中 (job_status={job_status})，{delay}s 后重试...")

    raise RuntimeError(
        f"Feishu import_task timed out after {_IMPORT_TIMEOUT_SECONDS}s (ticket={ticket})"
    )


def _sync_doc_to_wiki(
    token: str, md_path: str, title: str, space_id: str, file_data: bytes
) -> dict:
    """Import via wiki/v2/spaces API (知识库导入)."""
    import urllib.request
    import urllib.error
    import re
    from movietrace.feishu._http import build_multipart_body

    print(f"准备导入到知识库 (space_id={space_id})...")

    import_url = f"{OPEN_API_BASE}/wiki/v2/{space_id}/pages/import_docx"

    # wiki 导入使用 multipart/form-data
    file_name = Path(md_path).name if Path(md_path).name.endswith(".md") else f"{title}.md"
    fields: dict[str, "str | tuple[bytes, str, str]"] = {
        "file": (file_data, file_name, "text/markdown"),
        "title": title,
    }
    body, boundary = build_multipart_body(fields)

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": f"multipart/form-data; boundary={boundary}",
    }
    req = urllib.request.Request(import_url, data=body, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            resp_json = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body_err = e.read().decode("utf-8", errors="replace")[:300]
        body_err = re.sub(r'"access_token"\s*:\s*"[^"]+"', '"access_token":"***"', body_err)
        raise RuntimeError(f"Feishu wiki import HTTP {e.code}: {body_err}") from e

    if resp_json.get("code") != 0:
        code = resp_json.get("code")
        msg = resp_json.get("msg", "")
        if code in (99991663, 99991661, 1061045):
            raise RuntimeError(
                f"Feishu wiki import permission denied (code={code}): {msg}. "
                "Grant the app 'wiki:wiki' scope in the Feishu console."
            )
        raise RuntimeError(f"Feishu wiki import failed (code={code}): {msg}")

    result = resp_json.get("data", {})
    doc_token = result.get("obj_token", "")
    doc_url = result.get("url", "")
    if not doc_url and doc_token:
        doc_url = f"https://bytedance.feishu.cn/wiki/{doc_token}"

    print(f"导入完成: {doc_url}")
    return {"doc_url": doc_url, "doc_token": doc_token}
