"""Feishu "A库缺口" sub-table sync.

Reads current DB state (virtual_series + canonical_items + external_ids + api_cache)
directly — does NOT depend on content_updates event log.

Design: one row per virtual_series; upsert keyed by TMDb ID (unique per vs).
Auth: reuses fetch_tenant_access_token from feishu.baseline.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo

from movietrace.feishu.baseline import fetch_tenant_access_token
from movietrace.feishu._http import (
    OPEN_API_BASE,
    request_json,
    batch_create_records,
    batch_update_records,
    unwrap_text_field,
)

TZ = ZoneInfo("Asia/Shanghai")

# ── SQL ──────────────────────────────────────────────────────────────────────

_GAP_SQL = """
WITH a_lib_max AS (
  SELECT ci.virtual_series_id AS vs_id,
         MAX(ci.season_number) AS a_lib_max_season
  FROM canonical_items ci
  JOIN external_ids ei ON ei.canonical_item_id = ci.id AND ei.source = 'upstream'
  WHERE ci.virtual_series_id IS NOT NULL
  GROUP BY ci.virtual_series_id
),
latest_cache AS (
  SELECT cache_key, response_json
  FROM (
    SELECT cache_key, response_json,
           ROW_NUMBER() OVER (PARTITION BY cache_key ORDER BY fetched_at DESC, id DESC) AS rn
    FROM api_cache
    WHERE cache_key LIKE 'tmdb:detail:%:tv'
  )
  WHERE rn = 1
),
tmdb_aired AS (
  SELECT vs.id AS vs_id,
         CAST(json_extract(lc.response_json, '$.last_episode_to_air.season_number') AS INTEGER) AS tmdb_aired_season
  FROM virtual_series vs
  LEFT JOIN latest_cache lc ON lc.cache_key = 'tmdb:detail:' || vs.tmdb_tv_id || ':tv'
),
recent_hot AS (
  SELECT ci.virtual_series_id AS vs_id,
         MAX(cu.hot_score) AS hot_score
  FROM content_updates cu
  JOIN canonical_items ci ON ci.id = cu.canonical_item_id
  WHERE cu.created_at >= datetime('now', '-30 days')
  GROUP BY ci.virtual_series_id
)
SELECT
  vs.id            AS vs_id,
  vs.name,
  CAST(vs.tmdb_tv_id AS TEXT)  AS tmdb_tv_id,
  vs.tmdb_status,
  COALESCE(alm.a_lib_max_season, 0)                       AS a_lib_max,
  ta.tmdb_aired_season,
  ta.tmdb_aired_season - COALESCE(alm.a_lib_max_season, 0) AS gap_count,
  COALESCE(rh.hot_score, 0)                               AS hot_score
FROM virtual_series vs
LEFT JOIN a_lib_max alm  ON alm.vs_id = vs.id
LEFT JOIN tmdb_aired ta  ON ta.vs_id  = vs.id
LEFT JOIN recent_hot rh  ON rh.vs_id  = vs.id
WHERE vs.poll_priority != 'skip'
  AND ta.tmdb_aired_season IS NOT NULL
  AND ta.tmdb_aired_season > COALESCE(alm.a_lib_max_season, 0)
ORDER BY COALESCE(rh.hot_score, 0) DESC, gap_count DESC;
"""


# ── Public API ───────────────────────────────────────────────────────────────

def compute_current_gaps(conn: sqlite3.Connection) -> list[dict]:
    """Query DB and return list of gap rows.

    Each row dict contains:
        vs_id, name, tmdb_tv_id, tmdb_status, a_lib_max, tmdb_aired_season,
        gap_count, hot_score, gap_seasons (str, e.g. "S4,S5")
    """
    rows = []
    cursor = conn.execute(_GAP_SQL)
    for r in cursor.fetchall():
        vs_id, name, tmdb_tv_id, tmdb_status, a_lib_max, tmdb_aired, gap_count, hot_score = r
        gap_seasons = ",".join(
            f"S{s}" for s in range(int(a_lib_max) + 1, int(tmdb_aired) + 1)
        )
        rows.append({
            "vs_id": vs_id,
            "name": name,
            "tmdb_tv_id": str(tmdb_tv_id) if tmdb_tv_id is not None else "",
            "tmdb_status": tmdb_status or "",
            "a_lib_max": int(a_lib_max),
            "tmdb_aired_season": int(tmdb_aired),
            "gap_count": int(gap_count),
            "hot_score": float(hot_score) if hot_score else 0.0,
            "gap_seasons": gap_seasons,
        })
    return rows


def sync_gap_table(
    rows: list[dict],
    *,
    app_id: str,
    app_secret: str,
    app_token: str,
    table_id: str,
    dry_run: bool = False,
) -> dict:
    """Upsert gap rows into the Feishu "A库缺口" sub-table.

    Upsert key: TMDb ID (unique per virtual_series).
    On create: 运营状态 defaults to "待补", 系统提示 defaults to "-".
    On update: 因 _build_fields 本身不输出 运营状态 / 备注 字段，update 自然不会覆盖人工编辑。

    Returns stats dict: total, created, updated, errors.
    """
    if dry_run:
        print(f"\n[DRY-RUN] 将 upsert {len(rows)} 行到 A库缺口 (table_id={table_id})")
        for i, row in enumerate(rows[:5]):
            print(f"  [{i+1}] {row['name']} (TMDb {row['tmdb_tv_id']}) "
                  f"A库S{row['a_lib_max']} → TMDb S{row['tmdb_aired_season']} "
                  f"gap={row['gap_count']} [{row['gap_seasons']}]")
        if len(rows) > 5:
            print(f"  ... 以及 {len(rows) - 5} 条更多")
        return {"total": len(rows), "created": 0, "updated": 0, "errors": 0, "dry_run": True}

    # 1. Auth
    token = fetch_tenant_access_token(app_id, app_secret)

    # 2. Fetch existing rows, build {tmdb_id: record_id} map
    existing_map = _fetch_all_by_tmdb_id(token, app_token, table_id)

    # 3. Build create / update lists
    now_ts = int(datetime.now(TZ).timestamp() * 1000)
    stats = {"total": len(rows), "created": 0, "updated": 0, "errors": 0}

    to_create: list[dict] = []
    to_update: list[tuple[str, dict]] = []

    for i, row in enumerate(rows):
        try:
            tmdb_id = row["tmdb_tv_id"]
            fields = _build_fields(row, now_ts)

            if tmdb_id in existing_map:
                # _build_fields 不输出 运营状态 / 备注 字段 → update 自然保留人工编辑
                to_update.append((existing_map[tmdb_id], fields))
            else:
                # New row — set defaults
                fields["运营状态"] = "待补"
                fields["系统提示"] = "-"
                to_create.append({"fields": fields})

        except Exception as exc:
            stats["errors"] += 1
            print(f"  ERROR [{i+1}] {row.get('name', '?')}: {exc}")

    # 4. Batch create (500 per batch, aligns with batch_update_records limit) — count only after success
    batch_size = 500
    for start in range(0, len(to_create), batch_size):
        batch = to_create[start:start + batch_size]
        try:
            batch_create_records(token, app_token, table_id, batch)
            stats["created"] += len(batch)
        except Exception as exc:
            print(f"  ERROR batch_create [{start}:{start+len(batch)}]: {exc}")
            stats["errors"] += len(batch)

    # 5. Batch update existing records — count only after success
    if to_update:
        updates = [{"record_id": rid, "fields": fields} for rid, fields in to_update]
        try:
            batch_update_records(token, app_token, table_id, updates)
            stats["updated"] += len(to_update)
        except Exception as exc:
            print(f"  ERROR batch_update {len(to_update)} records: {exc}")
            stats["errors"] += len(to_update)

    return stats


# ── Field builder ─────────────────────────────────────────────────────────────

def _build_fields(row: dict, now_ts: int) -> dict:
    """Build Feishu field dict for a gap row (use field names, not IDs).

    Does NOT include 运营状态 / 系统提示 / 备注 — caller decides.
    """
    return {
        "剧集名":         str(row["name"]),
        "TMDb ID":       str(row["tmdb_tv_id"]),
        "缺口类型":       "季",
        "A库当前最大季":  float(row["a_lib_max"]),
        "TMDb 已播季":   float(row["tmdb_aired_season"]),
        "缺口数":         float(row["gap_count"]),
        "缺口季":         str(row["gap_seasons"]),
        "TMDb 状态":     row["tmdb_status"],  # already normalized to str in compute_current_gaps
        "hot_score":     float(row["hot_score"]),
        "最近刷新时间":   now_ts,
    }


# ── REST helpers ──────────────────────────────────────────────────────────────

def _fetch_all_by_tmdb_id(token: str, app_token: str, table_id: str) -> dict[str, str]:
    """Fetch all existing records and return {tmdb_id: record_id}."""
    url = f"{OPEN_API_BASE}/bitable/v1/apps/{app_token}/tables/{table_id}/records/search"
    result: dict[str, str] = {}
    page_token = ""

    while True:
        payload: dict = {"page_size": 500}
        if page_token:
            payload["page_token"] = page_token

        resp = request_json("POST", url, token=token, payload=payload)
        if resp.get("code") != 0:
            raise RuntimeError(f"fetch records failed: {resp}")

        data = resp.get("data", {})
        for item in data.get("items", []):
            fields = item.get("fields", {})
            # TMDb ID is a text field — API may return list of rich-text segments
            tmdb_val = unwrap_text_field(fields.get("TMDb ID", ""))
            record_id = item.get("record_id", "")
            if tmdb_val and record_id:
                result[str(tmdb_val)] = record_id

        if not data.get("has_more"):
            break
        page_token = data.get("page_token", "")
        if not page_token:
            break

    return result
