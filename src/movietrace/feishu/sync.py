"""Feishu bitable sync — record upsert via REST API, keyed by field ID.

Bitable operations use the app credentials from secrets.json (same as baseline.py),
NOT lark-cli bot identity, to avoid cross-app permission issues.
Doc sync uses lark-cli (bot identity, which has docx:document:create scope).

Table and fields are pre-created via Feishu UI/API; this module does NOT auto-create.
"""

from __future__ import annotations

import json
import subprocess
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from movietrace.feishu.baseline import fetch_tenant_access_token

TZ = ZoneInfo("Asia/Shanghai")
OPEN_API_BASE = "https://open.feishu.cn/open-apis"

# ── Field ID map (table: 发现运行日志, 2026-05-16) ─────────────────────────
# Field IDs are stable across renames; Chinese names in comments for readability.
#
#   fldsqzJdpt       → 标题          (text, primary)
#   fldQAjQYS3       → 发现日期       (date)
#   fldhMhFwfV       → content_update_id (text)
#   fldeHJXf1a       → 类型          (select: TV/Movie)
#   fld6PkSLo1       → 更新类型       (select: new_discovery/new_season/re_promotion)
#   fldnywX91r       → 优先级         (select: P0/P1/P2)
#   fldjqIzdkN       → hot_score     (number)
#   fld0yUemzc       → 季号          (number)
#   fldP8KPqVk       → TMDb TV ID    (text)
#   fldL0PhEUG       → 是否低置信度    (select: 是/否)
#   fldjQdgnUW       → 数据源状态      (text)
#   fldkSISjWq       → 检测时间       (date: yyyy/MM/dd HH:mm)
#   fldWcf5728       → 同步时间       (date: yyyy/MM/dd HH:mm)
#   fldQwImuZb       → 同步批次       (text)
#   fldvnnoli7       → 运营状态       (select: 待看/确认加入/不加入)
#   fldaKaqzdO       → 运营备注       (text)
#   fldeG4aCTn       → 供应商状态      (select: 未提交/已提交/有货/无货)
#   fldp05S9Pz       → 负责人         (user)

# Re-export for callers that need field IDs directly
F = {
    "标题":             "fldsqzJdpt",
    "发现日期":          "fldQAjQYS3",
    "content_update_id": "fldhMhFwfV",
    "类型":             "fldeHJXf1a",
    "更新类型":          "fld6PkSLo1",
    "优先级":            "fldnywX91r",
    "hot_score":        "fldjqIzdkN",
    "季号":             "fld0yUemzc",
    "TMDb TV ID":       "fldP8KPqVk",
    "是否低置信度":        "fldL0PhEUG",
    "数据源状态":         "fldjQdgnUW",
    "检测时间":          "fldkSISjWq",
    "同步时间":          "fldWcf5728",
    "同步批次":          "fldQwImuZb",
    "运营状态":          "fldvnnoli7",
    "运营备注":          "fldaKaqzdO",
    "供应商状态":         "fldeG4aCTn",
    "负责人":            "fldp05S9Pz",
}

# field_id used for date-filter queries
_FID_DATE = F["发现日期"]
_FID_CONTENT_UPDATE_ID = F["content_update_id"]


# ── REST API helpers ──────────────────────────────────────────────────────

def _request_json(
    method: str,
    url: str,
    *,
    token: str | None = None,
    payload: dict | None = None,
) -> dict:
    headers = {"Content-Type": "application/json; charset=utf-8"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = None
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Feishu API HTTP {e.code}: {body[:500]}") from e


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
                        "field_name": _FID_DATE,  # 发现日期
                        "operator": "is",
                        "value": [run_date],
                    }
                ],
            },
            "page_size": 500,
        }
        if page_token:
            payload["page_token"] = page_token

        resp = _request_json("POST", url, token=token, payload=payload)
        if resp.get("code") != 0:
            raise RuntimeError(f"list records for date failed: {resp}")

        data = resp.get("data", {})
        for item in data.get("items", []):
            fields = item.get("fields", {})
            # API may return rich-text segments for text fields
            cid_val = fields.get(_FID_CONTENT_UPDATE_ID, "")  # content_update_id
            if isinstance(cid_val, list):
                cid_val = "".join(seg.get("text", "") for seg in cid_val)
            record_id = item.get("record_id", "")
            if cid_val and record_id:
                lookup[cid_val] = record_id

        if not data.get("has_more"):
            break
        page_token = data.get("page_token", "")
        if not page_token:
            break

    return lookup


def _create_records(token: str, app_token: str, table_id: str, records: list[dict]) -> None:
    """Batch create records. Each record is {fields: {field_id: value}}."""
    url = f"{OPEN_API_BASE}/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_create"
    payload = {"records": records}
    resp = _request_json("POST", url, token=token, payload=payload)
    if resp.get("code") != 0:
        raise RuntimeError(f"batch create records failed: {resp}")


def _update_record(token: str, app_token: str, table_id: str, record_id: str, fields: dict) -> None:
    """Update a single record's fields, keyed by field_id."""
    url = f"{OPEN_API_BASE}/bitable/v1/apps/{app_token}/tables/{table_id}/records/{record_id}"
    payload = {"fields": fields}
    resp = _request_json("PUT", url, token=token, payload=payload)
    if resp.get("code") != 0:
        raise RuntimeError(f"update record {record_id} failed: {resp}")


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
    now_str = datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")

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

            # Build fields dict keyed by field_id, Chinese name in comment
            fields = {
                F["发现日期"]:          run_date,
                F["content_update_id"]: snapshot_key,
                F["标题"]:             str(rec.get("title", "")),
                F["类型"]:             _derive_content_type(rec),
                F["更新类型"]:          str(rec.get("update_type", "")),
                F["优先级"]:            str(rec.get("priority", "")),
                F["hot_score"]:        float(rec.get("hot_score") or 0),
                F["季号"]:             int(rec.get("season") or 0),
                F["TMDb TV ID"]:       str(rec.get("tmdb_tv_id") or ""),
                F["是否低置信度"]:        bool(rec.get("match_confidence_low", False)),
                F["数据源状态"]:         source_status_str,
                F["检测时间"]:          str(rec.get("event_written_at", "")),
                F["同步时间"]:          now_str,
                F["同步批次"]:          run_date,
            }

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
                fields[F["运营状态"]] = "待看"
                fields[F["运营备注"]] = ""
                fields[F["供应商状态"]] = "未提交"
                fields[F["负责人"]] = ""
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
            _create_records(token, app_token, table_id, batch)
        except Exception as e:
            print(f"  ERROR batch create [{start}:{start+len(batch)}]: {e}")
            stats["errors"] += len(batch)
            stats["created"] -= len(batch)

    # 5. Update existing records one by one
    for record_id, fields in to_update:
        try:
            _update_record(token, app_token, table_id, record_id, fields)
        except Exception as e:
            print(f"  ERROR update record {record_id}: {e}")
            stats["errors"] += 1
            stats["updated"] -= 1

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
    cid = rec.get("content_update_id", "")
    if isinstance(cid, str):
        if ":movie:" in cid:
            return "movie"
        if ":tv:" in cid:
            return "tv"
    return "unknown"


# ── Doc sync (via lark-cli) ───────────────────────────────────────────────

def sync_doc(
    md_path: str,
    title: str,
    folder_token: str = "",
    *,
    dry_run: bool = False,
) -> dict:
    """Sync latest.md content as a Feishu document via lark-cli."""
    path = Path(md_path)
    content = path.read_text(encoding="utf-8")

    if dry_run:
        print(f"[DRY-RUN] 将创建飞书文档: {title}")
        print(f"[DRY-RUN] 内容长度: {len(content)} 字符")
        return {"doc_url": "", "doc_token": "", "dry_run": True}

    cmd = [
        "lark-cli", "docs", "+create",
        "--as", "bot",
        "--title", title,
        "--markdown", content,
    ]
    if folder_token:
        cmd.extend(["--folder-token", folder_token])

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        raise RuntimeError(f"lark-cli docs +create failed: {result.stderr[:500]}")

    stdout = result.stdout.strip()
    data = None
    lines = stdout.split("\n")
    for i, line in enumerate(lines):
        if line.strip().startswith("{"):
            candidate = "\n".join(lines[i:])
            try:
                data = json.loads(candidate)
                break
            except json.JSONDecodeError:
                continue
    if data is None:
        return {"doc_url": "", "doc_token": "", "_raw": stdout}

    inner = data.get("data", {}) if isinstance(data, dict) else {}
    doc_url = inner.get("doc_url", "") or inner.get("url", "")
    doc_token = inner.get("doc_id", "") or inner.get("document_id", "")
    return {"doc_url": doc_url, "doc_token": doc_token}
