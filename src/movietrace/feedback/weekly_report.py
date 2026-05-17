"""Generate weekly feedback markdown report from a Feishu pull JSON.

Sections A-E:
  A. Basic info (week number, dates, generation time)
  B. Hot table stats (last 7 days)
  C. Gap table stats (current snapshot)
  D. Key cases (rejected P0/P1, underscored accepted)
  E. V2 trigger condition checklist
"""
from __future__ import annotations

import json
import shutil
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Shanghai")

_NA = "N/A"


def _pct(num: int, denom: int) -> str:
    if denom == 0:
        return _NA
    return f"{num / denom * 100:.1f}%"


def _lookup_title(conn: sqlite3.Connection | None, tmdb_id: str) -> str:
    """Try to look up a title from B-library by tmdb_id. Returns '?' on miss."""
    if not tmdb_id or conn is None:
        return "?"
    try:
        row = conn.execute(
            """
            SELECT ci.title FROM canonical_items ci
            JOIN external_ids ei ON ei.canonical_item_id = ci.id
            WHERE ei.source = 'tmdb' AND ei.external_id = ?
            LIMIT 1
            """,
            (str(tmdb_id),),
        ).fetchone()
        return row[0] if row else "?"
    except Exception:
        return "?"


def generate_weekly_report(
    pull_data: dict,
    *,
    db_path: str | Path | None = None,
    output_dir: str | Path = "reports/feedback",
    dry_run: bool = False,
) -> str:
    """Generate a weekly markdown report from pull_data dict.

    Returns the report content string. Also saves to disk unless dry_run.
    """
    now = datetime.now(TZ)
    iso = now.isocalendar()
    year, week = iso.year, iso.week
    week_str = f"{year}-W{week:02d}"

    pulled_at = pull_data.get("pulled_at", "unknown")
    hot_data = pull_data.get("hot_table", {})
    gap_data = pull_data.get("gap_table", {})

    hot_records = hot_data.get("records", [])
    gap_records = gap_data.get("records", [])
    range_days = hot_data.get("range_days", 7)

    # Dates
    report_date = now.strftime("%Y-%m-%d")
    start_date = (now.date() - timedelta(days=range_days - 1)).strftime("%Y-%m-%d")

    # ── Section B: Hot table stats ──────────────────────────────────────────

    total_hot = len(hot_records)

    # operator_status distribution
    op_counts: dict[str, int] = {"待看": 0, "确认加入": 0, "不加入": 0, "空": 0}
    for r in hot_records:
        s = r.get("operator_status", "")
        if s in op_counts:
            op_counts[s] += 1
        else:
            op_counts["空"] += 1

    filled = total_hot - op_counts["空"]
    fill_rate = _pct(filled, total_hot)
    adopted = op_counts["确认加入"]
    decided = adopted + op_counts["不加入"]
    adopt_rate = _pct(adopted, decided)

    # Priority × operator_status cross table
    priorities = ["P0", "P1", "P2"]
    op_statuses = ["待看", "确认加入", "不加入", "空"]
    cross: dict[str, dict[str, int]] = {p: {s: 0 for s in op_statuses} for p in priorities + ["其他"]}
    for r in hot_records:
        p = r.get("priority", "其他")
        if p not in cross:
            p = "其他"
        s = r.get("operator_status", "")
        if s not in op_statuses:
            s = "空"
        cross[p][s] += 1

    # Vendor status
    vendor_counts: dict[str, int] = {"未提交": 0, "已提交": 0, "有货": 0, "无货": 0, "空": 0}
    for r in hot_records:
        v = r.get("vendor_status", "")
        if v in vendor_counts:
            vendor_counts[v] += 1
        else:
            vendor_counts["空"] += 1

    # ── Section C: Gap table stats ──────────────────────────────────────────

    total_gap = len(gap_records)
    gap_status_counts: dict[str, int] = {"待补": 0, "部分补充": 0, "已补": 0, "跳过": 0, "空": 0}
    for r in gap_records:
        s = r.get("operator_status", "")
        if s in gap_status_counts:
            gap_status_counts[s] += 1
        else:
            gap_status_counts["空"] += 1

    advanced = gap_status_counts["已补"] + gap_status_counts["跳过"]
    advance_rate = _pct(advanced, total_gap)

    # Top 10 by hot_score with 待补 status
    pending = [r for r in gap_records if r.get("operator_status", "") in ("待补", "")]
    pending_sorted = sorted(pending, key=lambda r: r.get("hot_score") or 0.0, reverse=True)[:10]

    # ── Section D: Key cases ────────────────────────────────────────────────

    # Rejected P0/P1
    rejected_high = [
        r for r in hot_records
        if r.get("operator_status") == "不加入" and r.get("priority") in ("P0", "P1")
    ][:10]

    # Accepted with low score (< 60)
    low_score_accepted = [
        r for r in hot_records
        if r.get("operator_status") == "确认加入"
        and r.get("hot_score") is not None
        and float(r["hot_score"]) < 60
    ][:10]

    # ── Section E: V2 trigger check ─────────────────────────────────────────

    # Count notes this "week" — any operator_note non-empty
    new_notes = [r for r in hot_records if r.get("operator_note", "").strip()]

    # ── Build markdown ───────────────────────────────────────────────────────

    lines: list[str] = []

    lines += [
        f"# MovieTrace V1 运营反馈周报 {week_str}",
        "",
        f"> 由 `export-feedback-report` 自动生成。数据拉取时间：{pulled_at}",
        "",
        "---",
        "",
        "## A. 基本信息",
        "",
        f"| 项目 | 值 |",
        f"|------|-----|",
        f"| 周编号 | {week_str} |",
        f"| 热点发现统计范围 | {start_date} ~ {report_date}（最近 {range_days} 天）|",
        f"| 缺口表快照时间 | {pulled_at} |",
        f"| 报告生成时间 | {now.strftime('%Y-%m-%d %H:%M')} +08 |",
        "",
    ]

    lines += [
        "## B. 热点发现表统计",
        "",
        f"**总候选数（近 {range_days} 天）：{total_hot}**",
        "",
        "### 运营状态分布",
        "",
        "| 状态 | 数量 | 占比 |",
        "|------|------|------|",
    ]
    for s in ["待看", "确认加入", "不加入", "空"]:
        lines.append(f"| {s} | {op_counts[s]} | {_pct(op_counts[s], total_hot)} |")

    lines += [
        "",
        f"- **运营回填率**：{fill_rate}（有运营状态行 {filled} / 总 {total_hot}）",
        f"- **采纳率**：{adopt_rate}（确认加入 {adopted} / 已决策 {decided}）",
        "",
        "### 优先级 × 运营状态交叉表",
        "",
        "| 优先级 | 待看 | 确认加入 | 不加入 | 空 | 合计 |",
        "|--------|------|----------|--------|-----|------|",
    ]
    for p in priorities + ["其他"]:
        row = cross[p]
        total_p = sum(row.values())
        if total_p == 0:
            continue
        lines.append(
            f"| {p} | {row['待看']} | {row['确认加入']} | {row['不加入']} | {row['空']} | {total_p} |"
        )

    lines += [
        "",
        "### 供应商推进状态",
        "",
        "| 状态 | 数量 |",
        "|------|------|",
    ]
    for v in ["未提交", "已提交", "有货", "无货", "空"]:
        if vendor_counts[v]:
            lines.append(f"| {v} | {vendor_counts[v]} |")
    lines.append("")

    lines += [
        "## C. A 库缺口表统计（当前快照）",
        "",
        f"**缺口 series 总数：{total_gap}**",
        "",
        "### 运营状态分布",
        "",
        "| 状态 | 数量 | 占比 |",
        "|------|------|------|",
    ]
    for s in ["待补", "部分补充", "已补", "跳过", "空"]:
        lines.append(f"| {s} | {gap_status_counts[s]} | {_pct(gap_status_counts[s], total_gap)} |")

    lines += [
        "",
        f"- **推进率（已补 + 跳过）**：{advance_rate}（{advanced} / {total_gap}）",
        "",
        "### Top 10 高热度待补 Series",
        "",
        "| 标题 | TMDb ID | 缺口季 | hot_score |",
        "|------|---------|--------|-----------|",
    ]
    _db_conn = sqlite3.connect(str(db_path)) if db_path else None
    try:
        for r in pending_sorted:
            title = r.get("name") or _lookup_title(_db_conn, r.get("tmdb_id", ""))
            lines.append(
                f"| {title} | {r.get('tmdb_id', '?')} | {r.get('gap_seasons', '?')} "
                f"| {r.get('hot_score', '?')} |"
            )
    finally:
        if _db_conn is not None:
            _db_conn.close()
    lines.append("")

    lines += [
        "## D. 关键案例",
        "",
        "### 被标「不加入」的 P0/P1 案例（误报信号）",
        "",
    ]
    if rejected_high:
        lines += [
            "| 标题 | 优先级 | hot_score | 运营备注 |",
            "|------|--------|-----------|----------|",
        ]
        for r in rejected_high:
            lines.append(
                f"| {r.get('title', '?')} | {r.get('priority', '?')} "
                f"| {r.get('hot_score', '?')} | {r.get('operator_note', '')} |"
            )
    else:
        lines.append("_本周无 P0/P1 被标「不加入」。_")
    lines.append("")

    lines += [
        "### 被标「确认加入」但 hot_score < 60 的案例（评分低估信号）",
        "",
    ]
    if low_score_accepted:
        lines += [
            "| 标题 | hot_score | 运营备注 |",
            "|------|-----------|----------|",
        ]
        for r in low_score_accepted:
            lines.append(
                f"| {r.get('title', '?')} | {r.get('hot_score', '?')} "
                f"| {r.get('operator_note', '')} |"
            )
    else:
        lines.append("_本周无 hot_score < 60 的确认加入案例。_")
    lines.append("")

    lines += [
        "## E. V2 触发条件检查",
        "",
        "| 条件 | 状态 | 备注 |",
        "|------|------|------|",
        "| V1 稳定运行 1-2 月 | 待积累 | 需人工评估累计天数 |",
        f"| 运营反馈具体需求短板 | 本周新备注 {len(new_notes)} 条 | {_first_notes(new_notes)} |",
        "| 技术栈或数据源瓶颈明显 | 否 | 待观察期后评估 |",
        "| 团队资源可承接 V2 | 否 | 待评估 |",
        "",
        "> V2 启动需四项全部满足，当前处于 V1 观察期积累阶段。",
        "",
    ]

    content = "\n".join(lines)

    if dry_run:
        print(f"\n[DRY-RUN] 周报预览（{week_str}）：")
        print(content[:800] + "\n... (截断)")
        return content

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"feedback_log_{week_str}.md"
    latest_path = out_dir / "feedback_latest.md"

    out_path.write_text(content, encoding="utf-8")
    shutil.copy2(out_path, latest_path)

    print(f"\n已写入周报: {out_path}")
    print(f"已更新: {latest_path}")
    return content


def _first_notes(records: list[dict], max_chars: int = 80) -> str:
    """Return a short excerpt of operator notes."""
    notes = [r.get("operator_note", "").strip() for r in records if r.get("operator_note", "").strip()]
    if not notes:
        return "无"
    sample = notes[0][:max_chars]
    suffix = "…" if len(notes[0]) > max_chars else ""
    return f'"{sample}{suffix}"' + (f" 等 {len(notes)} 条" if len(notes) > 1 else "")
