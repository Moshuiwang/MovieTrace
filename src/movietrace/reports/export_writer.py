from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from movietrace.db.schema import connect_database
from movietrace.pipeline.scoring import DEFAULT_WEIGHTS
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
        if report_kind == "hot":
            updates = _load_current_discovery_rows(conn, days)
        else:
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
                  upstream_agg.upstream_max_season,
                  ci.title_zh, ci.overview_zh, ci.genres_json, ci.networks_json,
                  upstream_agg.upstream_total_eps,
                  movie_eps.movie_upstream_eps
           from content_updates cu
           join canonical_items ci on ci.id = cu.canonical_item_id
           left join virtual_series vs on vs.id = ci.virtual_series_id
           left join (
               select ci2.virtual_series_id,
                      max(ci2.season_number) as upstream_max_season,
                      sum(ep_cnt.cnt) as upstream_total_eps
               from canonical_items ci2
               join external_ids ei on ei.canonical_item_id = ci2.id and ei.source = 'upstream'
               left join (
                   select fk_program_content_id, count(*) as cnt
                   from upstream_episodes
                   group by fk_program_content_id
               ) ep_cnt on ep_cnt.fk_program_content_id = cast(ei.external_id as integer)
               group by ci2.virtual_series_id
           ) upstream_agg on upstream_agg.virtual_series_id = ci.virtual_series_id
           left join (
               select ei2.canonical_item_id,
                      count(ue.id) as movie_upstream_eps
               from external_ids ei2
               left join upstream_episodes ue on ue.fk_program_content_id = cast(ei2.external_id as integer)
               where ei2.source = 'upstream'
               group by ei2.canonical_item_id
           ) movie_eps on movie_eps.canonical_item_id = ci.id
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
            "title_zh": r[16],
            "overview_zh": r[17],
            "genres_json": r[18],
            "networks_json": r[19],
            # TV: sum from virtual_series; movie: count per canonical_item
            "upstream_total_eps": r[20] if r[9] == "tv" else r[21],
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

    # For movie records, backfill imdb_id from api_cache (TMDb detail response includes it).
    need_imdb = []
    for i, row in enumerate(result):
        parts = (row["content_update_id"] or "").split(":")
        if len(parts) >= 3 and parts[0] == "discovery" and parts[1] == "movie":
            need_imdb.append((i, parts[2]))
    if need_imdb:
        imdb_keys = [f"tmdb:detail:{tmdb_id}:movie" for _, tmdb_id in need_imdb]
        phs = ",".join("?" for _ in imdb_keys)
        imdb_rows = conn.execute(
            f"select cache_key, json_extract(response_json, '$.imdb_id') from api_cache where cache_key in ({phs})",
            imdb_keys,
        ).fetchall()
        imdb_map = {r[0].split(":")[2]: r[1] for r in imdb_rows if r[1]}
        for i, tmdb_id in need_imdb:
            if tmdb_id in imdb_map:
                result[i]["imdb_id"] = imdb_map[tmdb_id]

    # Backfill tmdb_total_episodes: movies = 1; TV = sum of aired season episode_count.
    today_str = date.today().isoformat()
    tv_need_eps: list[tuple[int, str]] = []
    for i, row in enumerate(result):
        if row.get("content_type") == "movie":
            result[i]["tmdb_total_episodes"] = 1
            continue
        tmdb_id = str(row.get("tmdb_tv_id") or "")
        if not tmdb_id:
            parts = (row.get("content_update_id") or "").split(":")
            if len(parts) >= 3 and parts[0] == "discovery" and parts[1] == "tv":
                tmdb_id = parts[2]
        if tmdb_id:
            tv_need_eps.append((i, tmdb_id))
        else:
            result[i]["tmdb_total_episodes"] = None

    if tv_need_eps:
        eps_keys = [f"tmdb:detail:{tmdb_id}:tv" for _, tmdb_id in tv_need_eps]
        phs = ",".join("?" for _ in eps_keys)
        eps_rows = conn.execute(
            f"select cache_key, json_extract(response_json, '$.seasons') from api_cache where cache_key in ({phs})",
            eps_keys,
        ).fetchall()
        tmdb_eps_map: dict[str, int] = {}
        for ck, seasons_json in eps_rows:
            if not seasons_json:
                continue
            try:
                seasons = json.loads(seasons_json)
                tid = ck.split(":")[2]
                total = sum(
                    s.get("episode_count", 0)
                    for s in seasons
                    if s.get("season_number", 0) > 0
                    and (s.get("air_date") or "") <= today_str
                    and s.get("air_date")
                )
                tmdb_eps_map[tid] = total
            except (ValueError, TypeError):
                pass
        for i, tmdb_id in tv_need_eps:
            result[i]["tmdb_total_episodes"] = tmdb_eps_map.get(tmdb_id)

    return result


def _load_current_discovery_rows(conn, days: int) -> list[dict]:
    """Load discovery rows from current_discovery_items (not content_updates).

    Uses last_discovered_date for the --days window so the semantics are
    "items observed within the last N days", not "events written within N days".
    """
    import sqlite3 as _sqlite3
    prev_factory = conn.row_factory
    conn.row_factory = _sqlite3.Row
    try:
        rows = conn.execute(
            """SELECT cdi.discovery_key, cdi.content_type, cdi.tmdb_id,
                      cdi.title, cdi.title_zh, cdi.latest_priority,
                      cdi.latest_hot_score, cdi.latest_source_summary_json,
                      cdi.first_discovered_date, cdi.last_discovered_date,
                      cdi.discovery_count, cdi.latest_baseline_match_status,
                      cdi.latest_match_confidence_low,
                      cdi.stable_metadata_json, cdi.updated_at,
                      ci.overview_zh, ci.genres_json, ci.networks_json,
                      vs.name as series_name, vs.tmdb_tv_id,
                      vs.local_max_season, vs.tmdb_number_of_seasons,
                      upstream_agg.upstream_max_season, upstream_agg.upstream_total_eps,
                      movie_eps.movie_upstream_eps
               FROM current_discovery_items cdi
               LEFT JOIN canonical_items ci ON ci.id = cdi.canonical_item_id
               LEFT JOIN virtual_series vs ON vs.id = ci.virtual_series_id
               LEFT JOIN (
                   select ci2.virtual_series_id,
                          max(ci2.season_number) as upstream_max_season,
                          sum(ep_cnt.cnt) as upstream_total_eps
                   from canonical_items ci2
                   join external_ids ei on ei.canonical_item_id = ci2.id and ei.source = 'upstream'
                   left join (
                       select fk_program_content_id, count(*) as cnt
                       from upstream_episodes group by fk_program_content_id
                   ) ep_cnt on ep_cnt.fk_program_content_id = cast(ei.external_id as integer)
                   group by ci2.virtual_series_id
               ) upstream_agg on upstream_agg.virtual_series_id = ci.virtual_series_id
               LEFT JOIN (
                   select ei2.canonical_item_id, count(ue.id) as movie_upstream_eps
                   from external_ids ei2
                   left join upstream_episodes ue on ue.fk_program_content_id = cast(ei2.external_id as integer)
                   where ei2.source = 'upstream'
                   group by ei2.canonical_item_id
               ) movie_eps on movie_eps.canonical_item_id = ci.id
               WHERE cdi.last_discovered_date >= DATE('now', ?)
               ORDER BY cdi.latest_hot_score DESC""",
            (f"-{days} days",),
        ).fetchall()
    finally:
        # C1: always restore row_factory even if SELECT raises
        conn.row_factory = prev_factory

    result = [
        {
            "content_update_id": row["discovery_key"],
            "update_type": "new_discovery",
            "priority": row["latest_priority"],
            "hot_score": row["latest_hot_score"],
            "title": row["title"],
            "title_zh": row["title_zh"],
            "content_type": row["content_type"],
            "match_confidence_low": row["latest_match_confidence_low"],
            "source_summary_json": row["latest_source_summary_json"],
            # A3: do NOT alias updated_at as created_at — that would make "today re-synced"
            # look like "today first discovered". Use the true semantic fields instead.
            # Callers that need a single event time should use last_discovered_date.
            "series_name": row["series_name"],
            "tmdb_tv_id": row["tmdb_tv_id"],
            "stored_local_max_season": row["local_max_season"],
            "stored_tmdb_number_of_seasons": row["tmdb_number_of_seasons"],
            "upstream_max_season": row["upstream_max_season"],
            "overview_zh": row["overview_zh"],
            "genres_json": row["genres_json"],
            "networks_json": row["networks_json"],
            "upstream_total_eps": row["upstream_total_eps"] if row["content_type"] == "tv" else row["movie_upstream_eps"],
            # Fields specific to current_discovery_items
            "first_discovered_date": row["first_discovered_date"],
            "last_discovered_date": row["last_discovered_date"],
            "discovery_count": row["discovery_count"],
        }
        for row in rows
    ]

    # Backfill stored_tmdb_number_of_seasons from api_cache for TV items missing it.
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

    # Backfill imdb_id for movie items from api_cache.
    need_imdb = []
    for i, row in enumerate(result):
        parts = (row["content_update_id"] or "").split(":")
        if len(parts) >= 3 and parts[0] == "discovery" and parts[1] == "movie":
            need_imdb.append((i, parts[2]))
    if need_imdb:
        imdb_keys = [f"tmdb:detail:{tmdb_id}:movie" for _, tmdb_id in need_imdb]
        phs = ",".join("?" for _ in imdb_keys)
        imdb_rows = conn.execute(
            f"select cache_key, json_extract(response_json, '$.imdb_id') from api_cache where cache_key in ({phs})",
            imdb_keys,
        ).fetchall()
        imdb_map = {r[0].split(":")[2]: r[1] for r in imdb_rows if r[1]}
        for i, tmdb_id in need_imdb:
            if tmdb_id in imdb_map:
                result[i]["imdb_id"] = imdb_map[tmdb_id]

    # Backfill tmdb_total_episodes: movies = 1; TV = sum of aired season episode_count.
    today_str = date.today().isoformat()
    tv_need_eps: list[tuple[int, str]] = []
    for i, row in enumerate(result):
        if row.get("content_type") == "movie":
            result[i]["tmdb_total_episodes"] = 1
            continue
        tmdb_id = str(row.get("tmdb_tv_id") or "")
        if not tmdb_id:
            parts = (row.get("content_update_id") or "").split(":")
            if len(parts) >= 3 and parts[0] == "discovery" and parts[1] == "tv":
                tmdb_id = parts[2]
        if tmdb_id:
            tv_need_eps.append((i, tmdb_id))
        else:
            result[i]["tmdb_total_episodes"] = None

    if tv_need_eps:
        eps_keys = [f"tmdb:detail:{tmdb_id}:tv" for _, tmdb_id in tv_need_eps]
        phs = ",".join("?" for _ in eps_keys)
        eps_rows = conn.execute(
            f"select cache_key, json_extract(response_json, '$.seasons') from api_cache where cache_key in ({phs})",
            eps_keys,
        ).fetchall()
        tmdb_eps_map: dict[str, int] = {}
        for ck, seasons_json in eps_rows:
            if not seasons_json:
                continue
            try:
                seasons = json.loads(seasons_json)
                tid = ck.split(":")[2]
                total = sum(
                    s.get("episode_count", 0)
                    for s in seasons
                    if s.get("season_number", 0) > 0
                    and (s.get("air_date") or "") <= today_str
                    and s.get("air_date")
                )
                tmdb_eps_map[tid] = total
            except (ValueError, TypeError):
                pass
        for i, tmdb_id in tv_need_eps:
            result[i]["tmdb_total_episodes"] = tmdb_eps_map.get(tmdb_id)

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
    stats: dict | None = None,
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
        # D1: discovery rows get 3 extra columns (首次发现 / 最近发现 / 发现次数);
        # non-discovery rows use the original 5-column layout.
        has_discovery = any(u.get("update_type") == "new_discovery" for u in other)
        if has_discovery:
            lines.extend([
                "",
                "## 📋 其他更新",
                "",
                f"**数量：** {len(other)}",
                "",
                "| 标题 | 类型 | 优先级 | hot_score | 检测时间 | 首次发现 | 最近发现 | 发现次数 |",
                "|------|------|--------|-----------|----------|----------|----------|----------|",
            ])
        else:
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
            # A3: for discovery rows use last_discovered_date (true semantic);
            # for other update types fall back to created_at.
            if u.get("update_type") == "new_discovery":
                time_val = u.get("last_discovered_date", "N/A") or "N/A"
                time_display = str(time_val)[:10]  # YYYY-MM-DD only for date strings
                if has_discovery:
                    first_d = str(u.get("first_discovered_date") or "N/A")[:10]
                    last_d = str(u.get("last_discovered_date") or "N/A")[:10]
                    cnt = u.get("discovery_count") if u.get("discovery_count") is not None else "N/A"
                    lines.append(
                        f"| {_esc(u.get('title', 'N/A'))} "
                        f"| {u.get('update_type', 'N/A')} "
                        f"| {u.get('priority', 'N/A')} "
                        f"| {hs:.1f} "
                        f"| {time_display} "
                        f"| {first_d} "
                        f"| {last_d} "
                        f"| {cnt} |"
                    )
                else:
                    lines.append(
                        f"| {_esc(u.get('title', 'N/A'))} "
                        f"| {u.get('update_type', 'N/A')} "
                        f"| {u.get('priority', 'N/A')} "
                        f"| {hs:.1f} "
                        f"| {time_display} |"
                    )
            else:
                raw = u.get("created_at", "N/A") or "N/A"
                time_display = str(raw)[:16]
                if has_discovery:
                    lines.append(
                        f"| {_esc(u.get('title', 'N/A'))} "
                        f"| {u.get('update_type', 'N/A')} "
                        f"| {u.get('priority', 'N/A')} "
                        f"| {hs:.1f} "
                        f"| {time_display} "
                        f"| N/A "
                        f"| N/A "
                        f"| N/A |"
                    )
                else:
                    lines.append(
                        f"| {_esc(u.get('title', 'N/A'))} "
                        f"| {u.get('update_type', 'N/A')} "
                        f"| {u.get('priority', 'N/A')} "
                        f"| {hs:.1f} "
                        f"| {time_display} |"
                    )

    if not updates:
        lines.append("*暂无更新事件*")

    lines.extend(_render_scoring_rules())
    # Use provided stats or derive minimal stats from updates for funnel display
    effective_stats = stats or {"total_passed": len(updates), "filtered_out": []}
    lines.extend(_render_funnel(effective_stats))
    lines.extend(_render_errors(updates))

    return "\n".join(lines) + "\n"


_WEIGHT_DISPLAY: list[tuple[str, str, str]] = [
    ("flixpatrol", "FlixPatrol 热度", "flixpatrol_score"),
    ("tmdb_popularity", "TMDb 流行度", "tmdb_popularity_score"),
    ("trakt", "Trakt 热度", "trakt_score"),
    ("tmdb_rating", "TMDb 评分", "tmdb_rating_score"),
    ("imdb_rating", "IMDb 评分", "imdb_rating_score"),
    ("platform_weight", "平台权重", "platform_weight_score"),
    ("content_type", "内容类型", "content_type_score"),
    ("freshness", "新鲜度", "freshness_score"),
    ("language", "语言", "language_score"),
]


def _render_scoring_rules() -> list[str]:
    """Generate '⚖️ 评分规则与权重' section lines."""
    w = DEFAULT_WEIGHTS.get("weights", {})
    thresholds = DEFAULT_WEIGHTS.get("priority_thresholds", {"P0": 85, "P1": 70, "P2": 50})
    lines = [
        "",
        "## ⚖️ 评分规则与权重",
        "",
        "| 维度 | 权重 | 来源字段 |",
        "|------|------|----------|",
    ]
    for key, label, field in _WEIGHT_DISPLAY:
        pct = f"{w.get(key, 0) * 100:.0f}%"
        lines.append(f"| {label} | {pct} | `{field}` |")
    lines.extend([
        "",
        f"阈值：P0 ≥ {thresholds.get('P0', 85)} · P1 ≥ {thresholds.get('P1', 70)} · P2 ≥ {thresholds.get('P2', 50)}",
        "",
    ])
    return lines


def _render_funnel(stats: dict | None) -> list[str]:
    """Generate '🔍 过滤明细（漏斗）' section lines."""
    if not stats:
        return []
    total_merged = stats.get("total_merged")
    total_passed = stats.get("total_passed", 0)
    filtered_out = stats.get("filtered_out", [])
    eliminated = (total_merged - total_passed) if total_merged is not None else "N/A"

    lines = [
        "",
        "## 🔍 过滤明细（漏斗）",
        "",
        "| 阶段 | 数量 |",
        "|------|------|",
        f"| 多源合并候选 | {total_merged if total_merged is not None else 'N/A'} |",
        f"| 阈值过滤通过 | {total_passed} |",
        f"| 因低分淘汰 | {eliminated} |",
        "",
    ]
    if filtered_out:
        lines.extend([
            f"**被淘汰 Top {len(filtered_out)}（分数最高的未入选）：**",
            "",
            "| 名称 | hot_score | 类型 |",
            "|------|-----------|------|",
        ])
        extra = max(0, (total_merged - total_passed - len(filtered_out))) if total_merged is not None else 0
        for item in filtered_out:
            title = item.get("title", "N/A")
            score = item.get("hot_score", 0)
            ct = item.get("content_type", item.get("media_type", "N/A"))
            lines.append(f"| {title} | {score:.1f} | {ct} |")
        if extra > 0:
            lines.append("")
            lines.append(f"*另有 {extra} 项未列出*")
    lines.append("")
    return lines


def _render_errors(updates: list[dict]) -> list[str]:
    """Generate '⚠️ 异常 / 错误摘要' section lines from source_data_status in updates."""
    source_status = _extract_source_status(updates)
    error_lines: list[str] = []
    if source_status:
        for src_key, src_label in [("flixpatrol", "FlixPatrol"), ("tmdb", "TMDb"), ("trakt", "Trakt")]:
            info = source_status.get(src_key, {})
            if info.get("status") == "fallback":
                error_lines.append(f"- {src_label} fallback：使用 {info.get('snapshot_date', '?')} 缓存")
            elif info.get("status") == "failed_no_fallback":
                error_lines.append(f"- {src_label} 失败：无可用缓存")

    lines = [
        "",
        "## ⚠️ 异常 / 错误摘要",
        "",
    ]
    if error_lines:
        lines.extend(error_lines)
    else:
        lines.append("本次运行无异常 ✓")
    lines.append("")
    return lines


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
            # A3: for discovery rows, event_written_at reflects last_discovered_date
            # (the most recent date it was observed), not the DB row's updated_at.
            # For new_season rows, created_at is the real event timestamp.
            "event_written_at": (
                u.get("last_discovered_date")
                if u.get("update_type") == "new_discovery"
                else _format_db_utc_time(u.get("created_at"))
            ),
            "event_written_at_utc": (
                u.get("last_discovered_date")
                if u.get("update_type") == "new_discovery"
                else u.get("created_at")
            ),
            "source_data_status": source_info.get("source_data_status"),
            "created_at": u.get("created_at"),
            "upstream_max_season": upstream,
            "source_summary_json": u.get("source_summary_json"),
            "imdb_id": u.get("imdb_id"),
            "content_type": u.get("content_type"),
            "match_confidence_low": u.get("match_confidence_low"),
            "title_zh": u.get("title_zh"),
            "overview_zh": u.get("overview_zh"),
            "genres_json": u.get("genres_json"),
            "networks_json": u.get("networks_json"),
            "upstream_total_eps": u.get("upstream_total_eps"),
            "tmdb_total_episodes": u.get("tmdb_total_episodes"),
            "first_discovered_date": u.get("first_discovered_date"),
            "last_discovered_date": u.get("last_discovered_date"),
            "discovery_count": u.get("discovery_count"),
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
