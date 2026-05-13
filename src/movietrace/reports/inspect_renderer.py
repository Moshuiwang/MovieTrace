from __future__ import annotations

import json
from datetime import datetime

from movietrace.db.schema import connect_database


def format_table(updates: list[dict]) -> str:
    """Render updates as a terminal table."""
    if not updates:
        return "No updates found.\n"

    header = f"MovieTrace Updates (last 7 days)\n\n"
    cols = ["Priority", "Type", "Title", "hot_score", "Sources", "Created"]
    widths = [12, 16, 32, 10, 15, 12]

    lines = [header]
    lines.append(
        "| " + " | ".join(h.ljust(w) for h, w in zip(cols, widths)) + " |"
    )
    lines.append(
        "|-" + "-|-".join("-" * w for w in widths) + "-|"
    )

    for u in updates:
        hs = u.get("hot_score") or 0
        priority = f"{u.get('priority', 'N/A')} ({hs:.0f})"
        ptype = u.get("update_type", "N/A")
        title = _truncate(u.get("title", "N/A"), 30)
        hot = f"{hs:.1f}"
        sources = _parse_sources(u.get("source_summary_json", ""))
        created = (u.get("created_at", "") or "")[:10]

        row = [priority, ptype, title, hot, sources, created]
        lines.append(
            "| " + " | ".join(str(r).ljust(w) for r, w in zip(row, widths)) + " |"
        )

    # Summary
    p0 = sum(1 for u in updates if u.get("priority") == "P0")
    p1 = sum(1 for u in updates if u.get("priority") == "P1")
    p2 = sum(1 for u in updates if u.get("priority") == "P2")
    nd = sum(1 for u in updates if u.get("update_type") == "new_discovery")
    ns = sum(1 for u in updates if u.get("update_type") == "new_season")
    rp = sum(1 for u in updates if u.get("update_type") == "re_promotion")

    lines.append(
        f"\nTotal: {len(updates)} updates | P0: {p0} | P1: {p1} | P2: {p2}"
        f" | new_discovery: {nd} | new_season: {ns} | re_promotion: {rp}\n"
    )
    return "\n".join(lines)


def format_detail(update: dict) -> str:
    """Render a single update in detail."""
    lines = [
        f"content_update_id: {update.get('content_update_id', 'N/A')}",
        f"title: {update.get('title', 'N/A')}",
        f"priority: {update.get('priority', 'N/A')} (hot_score={update.get('hot_score', 0):.0f})",
        f"update_type: {update.get('update_type', 'N/A')}",
        f"created: {update.get('created_at', 'N/A')}",
        "",
        "热度依据:",
    ]

    source = _parse_source_json(update.get("source_summary_json", ""))
    if source:
        fp = source.get("fp")
        if fp:
            lines.append(
                f"- FlixPatrol: {fp.get('platform', '?')} #{fp.get('ranking', '?')}, "
                f"{fp.get('days_total', 0)}天在榜"
            )

        tmdb = source.get("tmdb")
        if tmdb:
            parts = [f"popularity={tmdb.get('popularity', '?')}"]
            if tmdb.get("vote_average"):
                parts.append(f"vote_average={tmdb['vote_average']}")
            if tmdb.get("vote_count"):
                parts.append(f"({tmdb['vote_count']} votes)")
            lines.append("- TMDb: " + ", ".join(parts))

        trakt = source.get("trakt")
        if trakt:
            parts = [f"watchers={trakt.get('watchers', '?')}"]
            if trakt.get("rating"):
                parts.append(f"rating={trakt['rating']}")
            if trakt.get("votes"):
                parts.append(f"({trakt['votes']} votes)")
            lines.append("- Trakt: " + ", ".join(parts))

        imdb = source.get("imdb")
        if imdb:
            lines.append(
                f"- IMDb: {imdb.get('rating', '?')}/{imdb.get('votes', '?')} votes"
            )

        if source.get("release_date"):
            lines.append(f"- Release date: {source['release_date']}")
        if source.get("language"):
            lines.append(f"- Language: {source['language']}")

    if not source:
        lines.append("- (暂无详细热度数据)")

    return "\n".join(lines)


def format_markdown_enhanced(updates: list[dict], days: int) -> str:
    """Render updates as enhanced markdown (P1.7-E multi-source version)."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "# MovieTrace 推荐导出",
        "",
        f"**导出时间：** {now}",
        f"**覆盖范围：** 最近 {days} 天",
        f"**总条数：** {len(updates)}",
        "",
        "---",
        "",
    ]

    new_seasons = [u for u in updates if u.get("update_type") == "new_season"]
    new_disc = [u for u in updates if u.get("update_type") == "new_discovery"]
    re_promo = [u for u in updates if u.get("update_type") == "re_promotion"]

    if new_disc:
        lines.extend([
            "## 🆕 新发现",
            "",
            f"**数量：** {len(new_disc)}",
            "",
            "| 标题 | 优先级 | hot_score | FP | TMDb | Trakt | IMDb | 检测时间 |",
            "|------|--------|-----------|-----|------|-------|------|----------|",
        ])
        for u in new_disc:
            s = _parse_source_json(u.get("source_summary_json", ""))
            fp_str = _fmt_fp_cell(s.get("fp"))
            tmdb_str = _fmt_tmdb_cell(s.get("tmdb"))
            trakt_str = _fmt_trakt_cell(s.get("trakt"))
            imdb_str = _fmt_imdb_cell(s.get("imdb"))
            lines.append(
                f"| {_esc(u.get('title', 'N/A'))} "
                f"| {u.get('priority', 'N/A')} "
                f"| {u.get('hot_score', 0):.1f} "
                f"| {fp_str} | {tmdb_str} | {trakt_str} | {imdb_str} "
                f"| {str(u.get('created_at', 'N/A'))[:16]} |"
            )

    if new_seasons:
        lines.extend([
            "",
            "## 📺 基线新季",
            "",
            f"**数量：** {len(new_seasons)}",
            "",
            "| 剧集 | 优先级 | 检测时间 |",
            "|------|--------|----------|",
        ])
        for u in new_seasons:
            lines.append(
                f"| {_esc(u.get('title', 'N/A'))} "
                f"| {u.get('priority', 'N/A')} "
                f"| {str(u.get('created_at', 'N/A'))[:16]} |"
            )

    if re_promo:
        lines.extend([
            "",
            "## ♻️ 已有可补充",
            "",
            f"**数量：** {len(re_promo)}",
            "",
            "| 标题 | 优先级 | hot_score | 检测时间 |",
            "|------|--------|-----------|----------|",
        ])
        for u in re_promo:
            lines.append(
                f"| {_esc(u.get('title', 'N/A'))} "
                f"| {u.get('priority', 'N/A')} "
                f"| {u.get('hot_score', 0):.1f} "
                f"| {str(u.get('created_at', 'N/A'))[:16]} |"
            )

    if not updates:
        lines.append("*暂无推荐更新*")

    return "\n".join(lines) + "\n"


def format_json_enhanced(updates: list[dict]) -> str:
    export = []
    for u in updates:
        source = _parse_source_json(u.get("source_summary_json", ""))
        export.append({
            "content_update_id": u.get("content_update_id"),
            "update_type": u.get("update_type"),
            "priority": u.get("priority"),
            "hot_score": u.get("hot_score"),
            "title": u.get("title"),
            "sources": source,
            "created_at": u.get("created_at"),
        })
    return json.dumps(export, indent=2, ensure_ascii=False)


def query_updates(
    db_path: str = "data/movietrace.db",
    days: int = 7,
    priority: str | None = None,
    update_type: str | None = None,
    content_update_id: str | None = None,
) -> list[dict]:
    """Query content_updates with optional filters."""
    conn = connect_database(db_path)
    try:
        if content_update_id:
            rows = conn.execute(
                """select cu.id, cu.content_update_id, cu.update_type, cu.priority,
                          cu.hot_score, cu.source_summary_json, cu.created_at,
                          ci.title, ci.content_type
                   from content_updates cu
                   left join canonical_items ci on ci.id = cu.canonical_item_id
                   where cu.content_update_id = ?""",
                (content_update_id,),
            ).fetchall()
        else:
            where = ["cu.created_at >= datetime('now', ?)"]
            params: list = [f"-{days} days"]
            if priority:
                pri_list = [p.strip() for p in priority.split(",")]
                placeholders = ",".join("?" for _ in pri_list)
                where.append(f"cu.priority in ({placeholders})")
                params.extend(pri_list)
            if update_type:
                where.append("cu.update_type = ?")
                params.append(update_type)

            sql = f"""select cu.id, cu.content_update_id, cu.update_type, cu.priority,
                             cu.hot_score, cu.source_summary_json, cu.created_at,
                             ci.title, ci.content_type
                      from content_updates cu
                      left join canonical_items ci on ci.id = cu.canonical_item_id
                      where {' and '.join(where)}
                      order by cu.hot_score desc"""

            rows = conn.execute(sql, params).fetchall()

        return [
            {
                "id": r[0],
                "content_update_id": r[1],
                "update_type": r[2],
                "priority": r[3],
                "hot_score": r[4],
                "source_summary_json": r[5],
                "created_at": r[6],
                "title": r[7] or "N/A",
                "content_type": r[8],
            }
            for r in rows
        ]
    finally:
        conn.close()


# ── Helpers ────────────────────────────────────────────────────────────


def _parse_source_json(raw: str) -> dict:
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}


def _parse_sources(raw: str) -> str:
    s = _parse_source_json(raw)
    flags = []
    fp = s.get("fp")
    if fp and isinstance(fp, dict) and fp:
        flags.append("FP")
    tmdb = s.get("tmdb")
    if tmdb and isinstance(tmdb, dict) and tmdb:
        flags.append("TMDb")
    trakt = s.get("trakt")
    if trakt and isinstance(trakt, dict) and trakt:
        flags.append("Trakt")
    if not flags:
        flags.append("(baseline)")
    return "/".join(flags)


def _truncate(s: str, max_len: int) -> str:
    if len(s) > max_len:
        return s[:max_len - 1] + "…"
    return s


def _fmt_fp_cell(fp: dict | None) -> str:
    if not fp:
        return "-"
    p = fp.get("platform", "?")[:2].upper()
    return f"{p}#{fp.get('ranking', '?')}/{fp.get('days_total', 0)}d"


def _fmt_tmdb_cell(tmdb: dict | None) -> str:
    if not tmdb:
        return "-"
    pop = tmdb.get("popularity", 0)
    return f"pop {pop:.0f}" if pop else "-"


def _fmt_trakt_cell(trakt: dict | None) -> str:
    if not trakt:
        return "-"
    w = trakt.get("watchers", 0)
    return f"{w} watchers" if w else "-"


def _fmt_imdb_cell(imdb: dict | None) -> str:
    if not imdb:
        return "-"
    return str(imdb.get("rating", "-"))


def _esc(text: str) -> str:
    return (text or "").replace("|", "\\|").replace("\n", " ")
