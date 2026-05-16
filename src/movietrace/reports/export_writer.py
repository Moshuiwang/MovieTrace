from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from movietrace.db.schema import connect_database
from movietrace.reports.inspect_renderer import _parse_source_json, _extract_source_status

TZ = ZoneInfo("Asia/Shanghai")


def export_recommendations(
    db_path: str = "data/movietrace.db",
    output_dir: str = "reports",
    days: int = 7,
    *,
    dry_run: bool = False,
) -> dict:
    """Export hot discovery content_updates as MD + JSON files.

    Returns {'md_path': str, 'json_path': str, 'total_items': int}.
    """
    return _export_updates(
        db_path=db_path,
        output_dir=output_dir,
        days=days,
        dry_run=dry_run,
        report_kind="hot",
    )


def export_baseline_updates(
    db_path: str = "data/movietrace.db",
    output_dir: str = "reports",
    days: int = 7,
    *,
    dry_run: bool = False,
) -> dict:
    """Export baseline new-season content_updates as separate MD + JSON files."""
    return _export_updates(
        db_path=db_path,
        output_dir=output_dir,
        days=days,
        dry_run=dry_run,
        report_kind="baseline",
    )


def _export_updates(
    *,
    db_path: str,
    output_dir: str,
    days: int,
    dry_run: bool,
    report_kind: str,
) -> dict:
    conn = connect_database(db_path)
    try:
        updates = _load_content_updates(conn, days, report_kind=report_kind)
        funnel = _build_baseline_funnel(conn, len(updates)) if report_kind == "baseline" else None
    finally:
        conn.close()

    if dry_run:
        print(f"[DRY-RUN] Would export {len(updates)} content_updates (last {days} days)")
        return {"md_path": "", "json_path": "", "total_items": len(updates), "dry_run": True}

    now = datetime.now()
    ts = now.strftime("%Y-%m-%d_%H%M")
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    md_content = format_markdown(updates, days, report_kind=report_kind, funnel=funnel)
    json_content = format_json(updates)

    if report_kind == "baseline":
        stem = "baseline_updates"
        latest_md_name = "baseline_latest.md"
        latest_json_name = "baseline_latest.json"
    else:
        stem = "recommendations"
        latest_md_name = "latest.md"
        latest_json_name = "latest.json"

    md_path = out / f"{stem}_{ts}.md"
    json_path = out / f"{stem}_{ts}.json"

    md_path.write_text(md_content, encoding="utf-8")
    json_path.write_text(json_content, encoding="utf-8")

    latest_md = out / latest_md_name
    latest_json = out / latest_json_name
    latest_md.write_text(md_content, encoding="utf-8")
    latest_json.write_text(json_content, encoding="utf-8")

    return {
        "md_path": str(md_path),
        "json_path": str(json_path),
        "latest_md": str(latest_md),
        "latest_json": str(latest_json),
        "total_items": len(updates),
    }


def _load_content_updates(conn, days: int, *, report_kind: str = "all") -> list[dict]:
    if report_kind == "baseline":
        type_clause = "and cu.update_type = 'new_season'"
    elif report_kind == "hot":
        type_clause = "and cu.update_type != 'new_season'"
    else:
        type_clause = ""

    rows = conn.execute(
        f"""select cu.id, cu.content_update_id, cu.update_type, cu.priority,
                  cu.hot_score, cu.match_confidence_low, cu.source_summary_json,
                  cu.created_at,
                  ci.title, ci.content_type, ci.content_granularity,
                  vs.name as series_name, vs.tmdb_tv_id,
                  vs.local_max_season, vs.tmdb_number_of_seasons,
                  upstream_agg.upstream_max_season
           from content_updates cu
           join canonical_items ci on ci.id = cu.canonical_item_id
           left join virtual_series vs on vs.id = ci.virtual_series_id
           left join (
               select ci2.virtual_series_id, max(ci2.season_number) as upstream_max_season
               from canonical_items ci2
               join external_ids ei on ei.canonical_item_id = ci2.id and ei.source = 'upstream'
               group by ci2.virtual_series_id
           ) upstream_agg on upstream_agg.virtual_series_id = ci.virtual_series_id
           where cu.created_at >= datetime('now', ?)
             {type_clause}
           order by cu.created_at desc""",
        (f"-{days} days",),
    ).fetchall()

    result = [
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
            "stored_local_max_season": r[13],
            "stored_tmdb_number_of_seasons": r[14],
            "upstream_max_season": r[15],
        }
        for r in rows
    ]

    # For new_discovery TV items without virtual_series, fill tmdb_number_of_seasons
    # from api_cache so the season field can be populated.
    need_cache = []
    for i, row in enumerate(result):
        if row["stored_tmdb_number_of_seasons"] is not None:
            continue
        parts = (row["content_update_id"] or "").split(":")
        if len(parts) >= 3 and parts[0] == "discovery" and parts[1] == "tv":
            need_cache.append((i, parts[2]))
    if need_cache:
        cache_keys = [f"tmdb:detail:{tmdb_id}:tv" for _, tmdb_id in need_cache]
        phs = ",".join("?" for _ in cache_keys)
        cache_rows = conn.execute(
            f"select cache_key, json_extract(response_json, '$.number_of_seasons') from api_cache where cache_key in ({phs})",
            cache_keys,
        ).fetchall()
        cache_map = {r[0].split(":")[2]: int(r[1]) for r in cache_rows if r[1] is not None}
        for i, tmdb_id in need_cache:
            if tmdb_id in cache_map:
                result[i]["stored_tmdb_number_of_seasons"] = cache_map[tmdb_id]

    return result


def _build_baseline_funnel(conn, report_items: int) -> dict:
    """Build baseline report funnel counts from A-library rows to exported results."""
    online_flags = ("1", "true", "True", "TRUE", "Y", "yes", "online")
    placeholders = ",".join("?" for _ in online_flags)
    return {
        "upstream_programs_total": _count(conn, "select count(*) from upstream_programs"),
        "upstream_programs_online": _count(
            conn,
            f"select count(*) from upstream_programs where online_flag in ({placeholders})",
            online_flags,
        ),
        "upstream_season_like": _count(
            conn,
            "select count(*) from upstream_programs where name glob '*S[0-9][0-9]*'",
        ),
        "canonical_tv_seasons": _count(
            conn,
            """select count(*) from canonical_items
               where content_type = 'tv' and content_granularity = 'season'""",
        ),
        "virtual_series_total": _count(conn, "select count(*) from virtual_series"),
        "virtual_series_trackable": _count(
            conn, "select count(*) from virtual_series where poll_priority != 'skip'"
        ),
        "report_new_seasons": report_items,
    }


def _count(conn, sql: str, params: tuple | list = ()) -> int:
    row = conn.execute(sql, params).fetchone()
    return int(row[0] or 0) if row else 0


def format_markdown(
    updates: list[dict],
    days: int,
    *,
    report_kind: str = "all",
    funnel: dict | None = None,
) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S +08")
    if report_kind == "baseline":
        title = "# MovieTrace 基线新季追踪导出"
    elif report_kind == "hot":
        title = "# MovieTrace 热点内容发现导出"
    else:
        title = "# MovieTrace 更新事件导出"
    lines = [
        title,
        "",
        f"**导出时间：** {now}",
        f"**覆盖范围：** 最近 {days} 天",
        f"**总条数：** {len(updates)}",
        "",
    ]

    if report_kind == "baseline" and funnel:
        lines.extend([
            "## 漏斗数据",
            "",
            "| 阶段 | 条数 | 说明 |",
            "|------|------|------|",
            f"| A 库原始节目 | {funnel.get('upstream_programs_total', 0)} | `upstream_programs` 全量 |",
            f"| A 库在线节目 | {funnel.get('upstream_programs_online', 0)} | `online_flag` 为在线值 |",
            f"| A 库疑似季级 TV | {funnel.get('upstream_season_like', 0)} | 名称包含 `Sxx` 的节目 |",
            f"| B 库 TV season | {funnel.get('canonical_tv_seasons', 0)} | 已规范化为 TV season 的条目 |",
            f"| 聚合剧集 | {funnel.get('virtual_series_total', 0)} | `virtual_series` 剧集维度 |",
            f"| 可追踪剧集 | {funnel.get('virtual_series_trackable', 0)} | 排除 `poll_priority=skip` |",
            f"| 当前报告结果 | {funnel.get('report_new_seasons', 0)} | 最近 {days} 天 `new_season` 事件 |",
            "",
        ])

    # Source data status summary (P1.10-E)
    source_status = _extract_source_status(updates)
    if report_kind == "baseline":
        source_status = None
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
    elif report_kind != "baseline":
        lines.extend([
            "> ⚠️ 未检测到数据源状态（旧记录或 dry-run 模式下不会记录）。",
            "",
        ])

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
            "| 剧集 | TMDb ID | A库当前季数 | TMDb当前季数 | 新季 | TMDb 状态 | 制作中 | 优先级 | hot_score | baseline检测时间 | 事件写入时间 |",
            "|------|---------|-------------|--------------|------|-----------|--------|--------|-----------|------------------|--------------|",
        ])
        for u in new_seasons:
            source_info = _parse_source_json(u.get("source_summary_json", ""))
            seasons = source_info.get("seasons")
            if seasons and len(seasons) > 1:
                season_label = f"S{min(seasons)}-S{max(seasons)}"
            else:
                season_label = f"S{source_info.get('season', '?')}"
            hs = u.get("hot_score") or 0
            baseline_local_max, blm_fallback = _baseline_local_max(source_info, u)
            tmdb_seasons = source_info.get("tmdb_number_of_seasons")
            if tmdb_seasons is None:
                tmdb_seasons = u.get("stored_tmdb_number_of_seasons")
            baseline_detected_at = (
                source_info.get("baseline_detected_at")
                or source_info.get("detected_at")
                or "N/A"
            )
            lines.append(
                f"| {_esc(u.get('series_name') or u.get('title', 'N/A'))} "
                f"| {u.get('tmdb_tv_id', 'N/A')} "
                f"| {_format_blm(baseline_local_max, blm_fallback)} "
                f"| {_format_optional_int(tmdb_seasons)} "
                f"| {season_label} "
                f"| {_esc(str(source_info.get('tmdb_status') or 'N/A'))} "
                f"| {source_info.get('in_production') if source_info.get('in_production') is not None else 'N/A'} "
                f"| {u.get('priority', 'N/A')} "
                f"| {hs:.1f} "
                f"| {_format_time(baseline_detected_at)} "
                f"| {_format_db_utc_time(u.get('created_at'))} |"
            )

    if other:
        lines.extend([
            "",
            "## 📋 其他更新",
            "",
            f"**数量：** {len(other)}",
            "",
            "| 标题 | 类型 | 优先级 | hot_score | 检测时间 |",
            "|------|------|--------|-----------|----------|",
        ])
        for u in other:
            hs = u.get("hot_score") or 0
            lines.append(
                f"| {_esc(u.get('title', 'N/A'))} "
                f"| {u.get('update_type', 'N/A')} "
                f"| {u.get('priority', 'N/A')} "
                f"| {hs:.1f} "
                f"| {u.get('created_at', 'N/A')[:16]} +08 |"
            )

    if not updates:
        lines.append("*暂无更新事件*")

    return "\n".join(lines) + "\n"


def format_json(updates: list[dict]) -> str:
    export = []
    for u in updates:
        source_info = _parse_source_json(u.get("source_summary_json", ""))
        blm_value, blm_fallback = _baseline_local_max(source_info, u)
        tmdb_seasons = (
            source_info.get("tmdb_number_of_seasons")
            if source_info.get("tmdb_number_of_seasons") is not None
            else u.get("stored_tmdb_number_of_seasons")
        )
        raw_season = source_info.get("season")
        # For new_discovery TV, season field is not set; use total seasons from TMDb instead.
        if not raw_season and u.get("update_type") == "new_discovery":
            raw_season = tmdb_seasons
        upstream = u.get("upstream_max_season")
        export.append({
            "content_update_id": u.get("content_update_id"),
            "update_type": u.get("update_type"),
            "priority": u.get("priority"),
            "hot_score": u.get("hot_score"),
            "title": u.get("title"),
            "series_name": u.get("series_name"),
            "tmdb_id": u.get("tmdb_tv_id") or _extract_tmdb_id_from_discovery_id(u.get("content_update_id", "")),
            "season": raw_season,
            "seasons": source_info.get("seasons"),
            "baseline_local_max_season": blm_value,
            "baseline_local_max_season_is_fallback": blm_fallback,
            "tmdb_number_of_seasons": tmdb_seasons,
            "tmdb_status": source_info.get("tmdb_status"),
            "in_production": source_info.get("in_production"),
            "last_episode_to_air": source_info.get("last_episode_to_air"),
            "next_episode_to_air": source_info.get("next_episode_to_air"),
            "baseline_detected_at": source_info.get("baseline_detected_at")
            or source_info.get("detected_at"),
            "event_written_at": _format_db_utc_time(u.get("created_at")),
            "event_written_at_utc": u.get("created_at"),
            "source_data_status": source_info.get("source_data_status"),
            "created_at": u.get("created_at"),
            "upstream_max_season": upstream,
        })
    return json.dumps(export, indent=2, ensure_ascii=False)


def _baseline_local_max(source_info: dict, update: dict) -> tuple[int | None, bool]:
    """Return (value, is_fallback). is_fallback=True means the value was estimated."""
    value = source_info.get("baseline_local_max_season")
    if value is not None:
        return _to_int(value), False
    season_min = _to_int(source_info.get("season_min"))
    if season_min is not None:
        return max(season_min - 1, 0), True
    season = _to_int(source_info.get("season"))
    if season is not None:
        return max(season - 1, 0), True
    return _to_int(update.get("stored_local_max_season")), True


def _extract_tmdb_id_from_discovery_id(content_update_id: str) -> str | None:
    """Extract TMDb ID from 'discovery:{tv|movie}:{id}:{date}' format IDs."""
    parts = content_update_id.split(":") if content_update_id else []
    if len(parts) >= 3 and parts[0] == "discovery":
        return parts[2]
    return None


def _to_int(value) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _format_blm(value: int | None, is_fallback: bool) -> str:
    """Format baseline_local_max: prefix ~ for fallback/estimated values."""
    parsed = _to_int(value) if value is not None else None
    if parsed is None:
        return "N/A"
    if is_fallback:
        return f"~{parsed}"
    return str(parsed)


def _format_optional_int(value) -> str:
    parsed = _to_int(value)
    return str(parsed) if parsed is not None else "N/A"


def _format_time(value) -> str:
    if not value:
        return "N/A"
    text = str(value)
    if text.endswith("+08"):
        return text[:19] + " +08"
    if len(text) >= 19:
        return text[:19]
    return text


def _format_db_utc_time(value) -> str:
    if not value:
        return "N/A"
    text = str(value)
    try:
        parsed = datetime.strptime(text[:19], "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return _format_time(text)
    local = parsed.replace(tzinfo=timezone.utc).astimezone(TZ)
    return local.strftime("%Y-%m-%d %H:%M:%S +08")



def _esc(text: str) -> str:
    return (text or "").replace("|", "\\|").replace("\n", " ")
