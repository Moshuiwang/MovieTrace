from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from movietrace.db.schema import connect_database


def export_recommendations(
    db_path: str = "data/movietrace.db",
    output_dir: str = "reports",
    days: int = 7,
    *,
    dry_run: bool = False,
) -> dict:
    """Export content_updates as MD + JSON files.

    Returns {'md_path': str, 'json_path': str, 'total_items': int}.
    """
    conn = connect_database(db_path)
    try:
        updates = _load_content_updates(conn, days)
    finally:
        conn.close()

    if dry_run:
        print(f"[DRY-RUN] Would export {len(updates)} content_updates (last {days} days)")
        return {"md_path": "", "json_path": "", "total_items": len(updates), "dry_run": True}

    now = datetime.now()
    ts = now.strftime("%Y-%m-%d_%H%M")
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    md_path = out / f"recommendations_{ts}.md"
    json_path = out / f"recommendations_{ts}.json"

    md_path.write_text(format_markdown(updates, days), encoding="utf-8")
    json_path.write_text(format_json(updates), encoding="utf-8")

    return {
        "md_path": str(md_path),
        "json_path": str(json_path),
        "total_items": len(updates),
    }


def _load_content_updates(conn, days: int) -> list[dict]:
    rows = conn.execute(
        """select cu.id, cu.content_update_id, cu.update_type, cu.priority,
                  cu.hot_score, cu.match_confidence_low, cu.source_summary_json,
                  cu.created_at,
                  ci.title, ci.content_type, ci.content_granularity,
                  vs.name as series_name, vs.tmdb_tv_id
           from content_updates cu
           join canonical_items ci on ci.id = cu.canonical_item_id
           left join virtual_series vs on vs.id = ci.virtual_series_id
           where cu.created_at >= datetime('now', ?)
           order by cu.created_at desc""",
        (f"-{days} days",),
    ).fetchall()

    return [
        {
            "id": r[0],
            "content_update_id": r[1],
            "update_type": r[2],
            "priority": r[3],
            "hot_score": r[4],
            "match_confidence_low": r[5],
            "source_summary_json": r[6],
            "created_at": r[7],
            "title": r[8],
            "content_type": r[9],
            "content_granularity": r[10],
            "series_name": r[11],
            "tmdb_tv_id": r[12],
        }
        for r in rows
    ]


def format_markdown(updates: list[dict], days: int) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "# MovieTrace 推荐导出",
        "",
        f"**导出时间：** {now}",
        f"**覆盖范围：** 最近 {days} 天",
        f"**总条数：** {len(updates)}",
        "",
    ]

    # Source data status summary (P1.10-E)
    source_status = _extract_source_status(updates)
    if source_status:
        lines.extend([
            "## 数据源状态",
            "",
        ])
        source_names = {"flixpatrol": "FlixPatrol", "tmdb": "TMDb", "trakt": "Trakt"}
        for src_key, src_label in source_names.items():
            ss = source_status.get(src_key, {})
            status = ss.get("status", "unknown")
            sdate = ss.get("snapshot_date")
            if status == "fresh":
                lines.append(f"- **{src_label}**: fresh ({sdate})")
            elif status == "fallback":
                lines.append(f"- **{src_label}**: ⚠️ fallback from {sdate}")
            elif status == "failed_no_fallback":
                lines.append(f"- **{src_label}**: ❌ failed_no_fallback")
            else:
                lines.append(f"- **{src_label}**: {status}")
        lines.append("")

    lines.extend([
        "---",
        "",
    ])

    new_seasons = [u for u in updates if u["update_type"] == "new_season"]
    other = [u for u in updates if u["update_type"] != "new_season"]

    if new_seasons:
        lines.extend([
            "## 📺 基线新季",
            "",
            f"**数量：** {len(new_seasons)}",
            "",
            "| 剧集 | TMDb ID | 更新类型 | 优先级 | 检测时间 |",
            "|------|---------|----------|--------|----------|",
        ])
        for u in new_seasons:
            source_info = _parse_source_json(u.get("source_summary_json", ""))
            lines.append(
                f"| {_esc(u.get('series_name') or u.get('title', 'N/A'))} "
                f"| {u.get('tmdb_tv_id', 'N/A')} "
                f"| 新季 S{source_info.get('season', '?')} "
                f"| {u.get('priority', 'N/A')} "
                f"| {u.get('created_at', 'N/A')[:19]} |"
            )

    if other:
        lines.extend([
            "",
            "## 📋 其他更新",
            "",
            f"**数量：** {len(other)}",
            "",
            "| 标题 | 类型 | 优先级 | 检测时间 |",
            "|------|------|--------|----------|",
        ])
        for u in other:
            lines.append(
                f"| {_esc(u.get('title', 'N/A'))} "
                f"| {u.get('update_type', 'N/A')} "
                f"| {u.get('priority', 'N/A')} "
                f"| {u.get('created_at', 'N/A')[:19]} |"
            )

    if not updates:
        lines.append("*暂无推荐更新*")

    return "\n".join(lines) + "\n"


def format_json(updates: list[dict]) -> str:
    export = []
    for u in updates:
        source_info = _parse_source_json(u.get("source_summary_json", ""))
        export.append({
            "content_update_id": u.get("content_update_id"),
            "update_type": u.get("update_type"),
            "priority": u.get("priority"),
            "title": u.get("title"),
            "series_name": u.get("series_name"),
            "tmdb_tv_id": u.get("tmdb_tv_id"),
            "season": source_info.get("season"),
            "source_data_status": source_info.get("source_data_status"),
            "created_at": u.get("created_at"),
        })
    return json.dumps(export, indent=2, ensure_ascii=False)


def _parse_source_json(raw: str) -> dict:
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}


def _esc(text: str) -> str:
    return (text or "").replace("|", "\\|").replace("\n", " ")


def _extract_source_status(updates: list[dict]) -> dict | None:
    """Extract source_data_status from the first update that has it."""
    for u in updates:
        source_info = _parse_source_json(u.get("source_summary_json", ""))
        status = source_info.get("source_data_status")
        if status:
            return status
    return None
