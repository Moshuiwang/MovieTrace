from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

from movietrace.db.schema import connect_database


def generate_daily_report(
    report_date: date | None = None,
    db_path: str = "data/movietrace.db",
) -> str:
    """Generate a daily Markdown report from candidate_matches data."""
    if report_date is None:
        report_date = date.today()

    conn = connect_database(db_path)
    try:
        rows = _load_report_data(conn)
    finally:
        conn.close()

    if not rows:
        return _empty_report(report_date)

    # Categorize
    new_discoveries = []
    existing = []
    needs_review = []

    for row in rows:
        is_in_base = bool(row["is_in_baseline"])
        confidence = row["match_confidence"]

        if confidence == "low":
            needs_review.append(row)
        elif is_in_base:
            existing.append(row)
        else:
            new_discoveries.append(row)

    # Sort by hot_score desc
    new_discoveries.sort(key=lambda r: r["hot_score"] or 0, reverse=True)
    existing.sort(key=lambda r: r["hot_score"] or 0, reverse=True)
    needs_review.sort(key=lambda r: r["hot_score"] or 0, reverse=True)

    # Build report
    lines = _build_report(report_date, new_discoveries, existing, needs_review)
    return "\n".join(lines) + "\n"


def _load_report_data(conn) -> list[dict]:
    sql = """
        select c.id, c.title, c.content_type, c.hot_score, c.priority,
               c.discovery_source, c.score_breakdown_json, c.reason_text,
               c.snapshot_date, c.tmdb_id, c.imdb_id,
               cm.is_in_baseline, cm.match_confidence, cm.match_method,
               cm.match_score_detail, cm.requires_human_review, cm.reason_text as match_reason,
               cm.baseline_item_id, b.title as baseline_title
        from candidates c
        join candidate_matches cm on cm.candidate_id = c.id
        left join baseline_items b on b.id = cm.baseline_item_id
        order by c.hot_score desc
    """
    rows = conn.execute(sql).fetchall()
    return [
        {
            "id": r[0],
            "title": r[1],
            "content_type": r[2],
            "hot_score": r[3],
            "priority": r[4],
            "discovery_source": r[5],
            "score_breakdown_json": r[6],
            "reason_text": r[7],
            "snapshot_date": r[8],
            "tmdb_id": r[9],
            "imdb_id": r[10],
            "is_in_baseline": r[11],
            "match_confidence": r[12],
            "match_method": r[13],
            "match_score_detail": r[14],
            "requires_human_review": r[15],
            "match_reason": r[16],
            "baseline_item_id": r[17],
            "baseline_title": r[18],
        }
        for r in rows
    ]


def _build_report(
    report_date: date,
    new_discoveries: list[dict],
    existing: list[dict],
    needs_review: list[dict],
) -> list[str]:
    total = len(new_discoveries) + len(existing) + len(needs_review)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    platforms = set()
    movie_count = 0
    tv_count = 0
    for item in new_discoveries + existing + needs_review:
        ct = item.get("content_type", "")
        if ct == "movie":
            movie_count += 1
        elif ct == "tv_show":
            tv_count += 1

    lines = [
        "# MovieTrace 每日发现日报",
        "",
        f"**生成时间：** {now}",
        f"**覆盖日期：** {report_date.isoformat()}",
        "**数据版本：** v1（Phase 1 MVP）",
        "",
        "---",
        "",
        "## 📊 统计汇总",
        "",
        "| 指标 | 数值 |",
        "|------|------|",
        f"| **🆕 新发现** | {len(new_discoveries)} |",
        f"| **♻️ 已有基线内容** | {len(existing)} |",
        f"| **⚠️ 待人工确认** | {len(needs_review)} |",
        f"| **总计候选** | {total} |",
        "| **覆盖平台** | Netflix, Prime Video, Disney+, Apple TV+, HBO Max, Hulu |",
        f"| **内容类型** | 电影 {movie_count} 部 / 剧集 {tv_count} 部 |",
        "",
        "---",
    ]

    # 🆕 新发现
    lines.extend(_section_new(new_discoveries))

    # ♻️ 已有
    lines.extend(_section_existing(existing))

    # ⚠️ 待确认
    lines.extend(_section_review(needs_review))

    lines.extend([
        "",
        "---",
        "",
        "## 备注",
        "",
        "- 日报基于 MovieTrace Phase 1 hot_score 评分公式和基线匹配规则生成",
        "- 低置信度候选标记为「待人工确认」，不会自动写入飞书",
        "- 已有基线内容可作为热度变化追踪，观察 hot_score 趋势",
    ])

    return lines


def _section_new(items: list[dict]) -> list[str]:
    lines = [
        "",
        "## 🆕 新发现（未在飞书基线中）",
        "",
        f"**数量：** {len(items)}",
        "",
    ]
    if not items:
        lines.append("*暂无新发现候选*")
        return lines

    lines.append("| 标题 | 类型 | hot_score | 优先级 | 发现来源 | 推荐理由 |")
    lines.append("|------|------|-----------|--------|----------|---------|")
    for item in items:
        lines.append(
            f"| {_esc(item['title'])} "
            f"| {_ct_label(item.get('content_type', ''))} "
            f"| {item['hot_score'] or 0:.0f} "
            f"| {item['priority'] or 'P3'} "
            f"| {item['discovery_source'] or ''} "
            f"| {_short_reason(item)} |"
        )
    return lines


def _section_existing(items: list[dict]) -> list[str]:
    lines = [
        "",
        "## ♻️ 已有基线内容",
        "",
        f"**数量：** {len(items)}",
        "",
    ]
    if not items:
        lines.append("*暂无已有基线候选*")
        return lines

    lines.append("| 标题 | 类型 | hot_score | 基线标题 | 匹配度 |")
    lines.append("|------|------|-----------|----------|--------|")
    for item in items:
        lines.append(
            f"| {_esc(item['title'])} "
            f"| {_ct_label(item.get('content_type', ''))} "
            f"| {item['hot_score'] or 0:.0f} "
            f"| {_esc(item.get('baseline_title', '') or 'N/A')} "
            f"| {item.get('match_confidence', '')} |"
        )
    return lines


def _section_review(items: list[dict]) -> list[str]:
    lines = [
        "",
        "## ⚠️ 待人工确认",
        "",
        f"**数量：** {len(items)}",
        "",
    ]
    if not items:
        lines.append("*暂无待确认候选*")
        return lines

    lines.append("| 标题 | 类型 | hot_score | 建议基线 | 不确定原因 | 操作 |")
    lines.append("|------|------|-----------|----------|-----------|------|")
    for item in items:
        baseline_ref = f"#{item['baseline_item_id']}" if item.get("baseline_item_id") else "N/A"
        score_detail = item.get("match_score_detail", 0) or 0
        reason = f"相似度 {score_detail:.2f} ({item.get('match_method', '')})"
        lines.append(
            f"| {_esc(item['title'])} "
            f"| {_ct_label(item.get('content_type', ''))} "
            f"| {item['hot_score'] or 0:.0f} "
            f"| {baseline_ref} "
            f"| {reason} "
            f"| 确认/驳回 |"
        )
    return lines


def _ct_label(content_type: str) -> str:
    return "🎬" if content_type == "movie" else "📺"


def _esc(text: str) -> str:
    return (text or "").replace("|", "\\|").replace("\n", " ")


def _short_reason(item: dict) -> str:
    """Build short reason text (≤60 chars) from score breakdown."""
    try:
        bd = json.loads(item.get("score_breakdown_json") or "{}")
    except (json.JSONDecodeError, TypeError):
        bd = {}

    parts = []
    fp_score = bd.get("flixpatrol_score")
    if fp_score and fp_score >= 80:
        parts.append("FP热度高")
    elif fp_score and fp_score >= 50:
        parts.append("FP在榜")

    if bd.get("tmdb_popularity_score"):
        parts.append("TMDb热门")

    if item.get("discovery_source") == "both":
        parts.append("强信号+新内容")
    elif item.get("discovery_source") == "new_release":
        parts.append("新上榜")

    if not parts:
        parts.append("FlixPatrol在榜")

    return "，".join(parts)[:60]


def _empty_report(report_date: date) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return (
        "# MovieTrace 每日发现日报\n\n"
        f"**生成时间：** {now}\n"
        f"**覆盖日期：** {report_date.isoformat()}\n"
        "**数据版本：** v1（Phase 1 MVP）\n\n"
        "---\n\n"
        "## 📊 统计汇总\n\n"
        "*暂无候选数据*\n\n"
        "> 请先运行数据采集和评分流水线（P1-B → P1-C → P1-D）\n"
    )


def write_daily_report(
    report_date: date | None = None,
    output_dir: str = "reports/daily",
    db_path: str = "data/movietrace.db",
) -> str:
    """Generate and write daily report to file. Returns file path."""
    if report_date is None:
        report_date = date.today()

    md = generate_daily_report(report_date, db_path)
    out_path = Path(output_dir) / f"{report_date.isoformat()}.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md, encoding="utf-8")
    return str(out_path)
