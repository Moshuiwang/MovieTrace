"""Feishu notification — send summary / alert messages via IM REST API, with Gmail stub."""

from __future__ import annotations

import json
import sys
from zoneinfo import ZoneInfo

from movietrace.feishu.baseline import fetch_tenant_access_token
from movietrace.feishu._http import OPEN_API_BASE, request_json

TZ = ZoneInfo("Asia/Shanghai")


def _send_text_message(
    token: str, receive_id: str, text: str, receive_id_type: str = "open_id"
) -> dict:
    """Send a text message via /im/v1/messages, return parsed response."""
    url = f"{OPEN_API_BASE}/im/v1/messages?receive_id_type={receive_id_type}"
    payload = {
        "receive_id": receive_id,
        "msg_type": "text",
        "content": json.dumps({"text": text}, ensure_ascii=False),
    }
    return request_json("POST", url, token=token, payload=payload)


def send_text(
    receive_id: str,
    text: str,
    *,
    app_id: str,
    app_secret: str,
    receive_id_type: str = "open_id",
) -> bool:
    """Send a plain text message to a Feishu user or group."""
    try:
        token = fetch_tenant_access_token(app_id, app_secret)
        result = _send_text_message(token, receive_id, text, receive_id_type=receive_id_type)
        if result.get("code") != 0:
            print(
                f"WARNING: feishu message send returned code={result.get('code')} msg={result.get('msg')}",
                file=sys.stderr,
            )
            return False
        return True
    except Exception as e:
        print(f"ERROR: feishu message send failed: {e}", file=sys.stderr)
        return False


# ── Interactive card (success notification) ───────────────────────────────


def _build_card(
    run_date: str,
    discover_stats: dict,
    sync_stats: dict,
    top_items: list,
    doc_url: str = "",
    table_url: str = "",
    log_file: str = "",
) -> dict:
    """Build Feishu interactive card JSON for daily summary."""
    has_errors = sync_stats.get("errors", 0) > 0
    header_color = "red" if has_errors else "green"

    elements: list[dict] = []

    # ── Section 1: data collection & pipeline ──────────────────────────────
    source_status = discover_stats.get("source_status", {})
    fp_info = source_status.get("flixpatrol", {})
    tmdb_info = source_status.get("tmdb", {})
    trakt_info = source_status.get("trakt", {})

    def _src_tag(info: dict, fetched: int) -> str:
        if info.get("status") == "fallback":
            return f"⚠️ 缓存({info.get('snapshot_date', '?')})"
        if info.get("status") == "failed_no_fallback":
            return "❌ 失败"
        return f"{fetched} 条 ✅"

    tmdb_fetched = discover_stats.get("tmdb_fetched", 0)
    trakt_fetched = discover_stats.get("trakt_fetched", 0)
    fp_fetched = discover_stats.get("flixpatrol_fetched", 0)

    total_merged = discover_stats.get("total_merged", 0)
    total_passed = discover_stats.get("total_passed", 0)
    written = discover_stats.get("written", 0)

    src_lines = (
        f"TMDb {_src_tag(tmdb_info, tmdb_fetched)}  ·  "
        f"Trakt {_src_tag(trakt_info, trakt_fetched)}  ·  "
        f"FlixPatrol {_src_tag(fp_info, fp_fetched)}"
    )
    pipeline_line = (
        f"合并去重 **{total_merged}** 条  →  通过 P2+ **{total_passed}** 条  →  本次新写入 **{written}** 条"
    )
    elements.append({
        "tag": "div",
        "text": {"tag": "lark_md", "content": f"**📡 数据采集**\n{src_lines}\n\n{pipeline_line}"},
    })
    elements.append({"tag": "hr"})

    # ── Section 2: priority distribution ──────────────────────────────────
    prio = discover_stats.get("priority", {})
    p0 = prio.get("P0", 0)
    p1 = prio.get("P1", 0)
    p2 = prio.get("P2", 0)
    total_prio = p0 + p1 + p2
    prio_text = (
        f"**📊 发现结果**\n"
        f"P0 **{p0}** 条  ·  P1 **{p1}** 条  ·  P2 **{p2}** 条  ·  合计 **{total_prio}** 条"
    )
    elements.append({"tag": "div", "text": {"tag": "lark_md", "content": prio_text}})
    elements.append({"tag": "hr"})

    # ── Section 3: Feishu table sync ──────────────────────────────────────
    s_total = sync_stats.get("total", 0)
    s_created = sync_stats.get("created", 0)
    s_updated = sync_stats.get("updated", 0)
    s_errors = sync_stats.get("errors", 0)
    err_tag = f"  🔴 错误 {s_errors}" if s_errors else ""
    sync_text = (
        f"**🔄 多维表格同步**\n"
        f"总计 {s_total}  ·  新建 **{s_created}**  ·  更新 **{s_updated}**{err_tag}"
    )
    elements.append({"tag": "div", "text": {"tag": "lark_md", "content": sync_text}})

    # ── Section 4: top P0/P1 items ────────────────────────────────────────
    important = [item for item in top_items if item.get("priority") in ("P0", "P1")]
    if important:
        elements.append({"tag": "hr"})
        lines = ["**🎯 重点内容（P0 / P1）**"]
        seen_titles: set[str] = set()
        for item in important:
            title = item.get("title", "")
            if title in seen_titles:
                continue
            seen_titles.add(title)
            if len(lines) > 10:  # header line + 10 items
                break
            pri = item.get("priority", "")
            score = item.get("hot_score", 0)
            lines.append(f"[{pri}] {title}  →  {score:.1f} 分")
        elements.append({"tag": "div", "text": {"tag": "lark_md", "content": "\n".join(lines)}})

    # ── Section 5: warnings ───────────────────────────────────────────────
    warnings: list[str] = []
    if fp_info.get("status") == "fallback":
        warnings.append(f"FlixPatrol：API 402，使用 {fp_info.get('snapshot_date', '?')} 缓存")
    if fp_info.get("status") == "failed_no_fallback":
        warnings.append("FlixPatrol：无可用数据（无缓存）")
    if s_errors:
        warnings.append(f"多维表格同步错误 {s_errors} 条")
    if warnings:
        elements.append({"tag": "hr"})
        warn_body = "\n".join(f"· {w}" for w in warnings)
        elements.append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": f"**⚠️ 异常提醒**\n{warn_body}"},
        })

    # ── Section 6: run progress summary (P1.37) ──────────────────────────
    source_status_prog = discover_stats.get("source_status", {})
    enrich_imdb = discover_stats.get("enrich_imdb_backfill", {})
    enrich_omdb_d = discover_stats.get("enrich_omdb", {})
    enrich_tmdb_d = discover_stats.get("enrich_tmdb_detail", {})

    def _prog_src_tag(src_key: str, fetched: int) -> str:
        info = source_status_prog.get(src_key, {})
        if info.get("status") == "fallback":
            count = info.get("cached_count", fetched)
            return f"⚠️ 缓存({info.get('snapshot_date', '?')}, {count}条)"
        if info.get("status") == "failed_no_fallback":
            return "❌ 无可用数据"
        return f"✓ {fetched}条新鲜"

    fp_fetched_prog = discover_stats.get("flixpatrol_fetched", 0)
    tmdb_fetched_prog = discover_stats.get("tmdb_fetched", 0)
    trakt_fetched_prog = discover_stats.get("trakt_fetched", 0)

    imdb_backfilled = enrich_imdb.get("backfilled", enrich_imdb.get("enriched", 0))
    imdb_total_prog = enrich_imdb.get("total", total_merged)
    omdb_enriched = enrich_omdb_d.get("enriched", 0)
    tmdb_enriched = enrich_tmdb_d.get("enriched", 0)

    prog_lines = [
        f"**⚙️ 运行进度**",
        f"[1/8] FlixPatrol: {_prog_src_tag('flixpatrol', fp_fetched_prog)}",
        f"[2/8] TMDb: {_prog_src_tag('tmdb', tmdb_fetched_prog)}",
        f"[3/8] Trakt: {_prog_src_tag('trakt', trakt_fetched_prog)}",
        f"[5/8] 合并: {total_merged}条候选",
        f"[6/8] 丰富化: IMDb {imdb_backfilled}/{imdb_total_prog} · OMDb {omdb_enriched}/{total_merged} · TMDb详情 {tmdb_enriched}/{total_merged}",
        f"[8/8] 写入: P0={p0} P1={p1} P2={p2}, 共写入{written}条",
    ]
    elements.append({"tag": "hr"})
    elements.append({
        "tag": "div",
        "text": {"tag": "lark_md", "content": "\n".join(prog_lines)},
    })

    # ── Action buttons ────────────────────────────────────────────────────
    actions: list[dict] = []
    if doc_url:
        actions.append({
            "tag": "button",
            "text": {"tag": "plain_text", "content": "查看今日文档"},
            "url": doc_url,
            "type": "default",
        })
    if table_url:
        actions.append({
            "tag": "button",
            "text": {"tag": "plain_text", "content": "打开多维表格"},
            "url": table_url,
            "type": "default",
        })
    if actions:
        elements.append({"tag": "action", "actions": actions})

    if log_file:
        elements.append({
            "tag": "note",
            "elements": [{"tag": "plain_text", "content": f"日志：{log_file}"}],
        })

    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": f"MovieTrace · {run_date}"},
            "template": header_color,
        },
        "elements": elements,
    }


def send_card(
    receive_id: str,
    run_date: str,
    discover_stats: dict,
    sync_stats: dict,
    top_items: list,
    doc_url: str = "",
    table_url: str = "",
    log_file: str = "",
    *,
    app_id: str,
    app_secret: str,
    receive_id_type: str = "open_id",
) -> bool:
    """Send daily summary as a Feishu interactive card."""
    try:
        token = fetch_tenant_access_token(app_id, app_secret)
        card = _build_card(run_date, discover_stats, sync_stats, top_items, doc_url, table_url, log_file)
        url = f"{OPEN_API_BASE}/im/v1/messages?receive_id_type={receive_id_type}"
        payload = {
            "receive_id": receive_id,
            "msg_type": "interactive",
            "content": json.dumps(card, ensure_ascii=False),
        }
        result = request_json("POST", url, token=token, payload=payload)
        if result.get("code") != 0:
            print(
                f"WARNING: feishu card send returned code={result.get('code')} msg={result.get('msg')}",
                file=sys.stderr,
            )
            return False
        return True
    except Exception as e:
        print(f"ERROR: feishu card send failed: {e}", file=sys.stderr)
        return False


# ── Text fallback (used for error/warning alerts and when no discover_stats) ──


def send_summary(
    receive_id: str,
    run_date: str,
    stats: dict,
    doc_url: str = "",
    log_file: str = "",
    *,
    app_id: str,
    app_secret: str,
    receive_id_type: str = "open_id",
) -> bool:
    """Send a daily summary as plain text (fallback when card not available)."""
    total = stats.get("total", 0)
    created = stats.get("created", 0)
    updated = stats.get("updated", 0)
    errors = stats.get("errors", 0)
    parts = [f"MovieTrace 每日发现完成 - {run_date}", ""]
    parts.append(f"同步结果：{'成功' if errors == 0 else '部分成功'}")
    parts.append(f"同步条数：{total} (新增 {created}, 更新 {updated}, 错误 {errors})")

    p0 = stats.get("p0_count")
    p1 = stats.get("p1_count")
    p2 = stats.get("p2_count")
    if p0 is not None:
        parts.append(f"优先级：P0={p0} / P1={p1 or 0} / P2={p2 or 0}")

    if doc_url:
        parts.append(f"飞书文档：{doc_url}")
    if log_file:
        parts.append(f"本地日志：{log_file}")

    text = "\n".join(parts)
    return send_text(receive_id, text, app_id=app_id, app_secret=app_secret, receive_id_type=receive_id_type)


def send_alert(
    receive_id: str,
    level: str,
    title: str,
    detail: str = "",
    log_file: str = "",
    *,
    app_id: str,
    app_secret: str,
    receive_id_type: str = "open_id",
) -> bool:
    """Send a failure/partial-success alert as plain text."""
    emoji = "❌" if level == "error" else "⚠️"
    parts = [
        f"{emoji} MovieTrace 运行告警 - {title}",
        f"级别：{level}",
    ]
    if detail:
        parts.append(f"详情：{detail}")
    if log_file:
        parts.append(f"本地日志：{log_file}")

    text = "\n".join(parts)
    return send_text(receive_id, text, app_id=app_id, app_secret=app_secret, receive_id_type=receive_id_type)


# ── Gmail SMTP (stub) ─────────────────────────────────────────────────────

def build_im_summary_text(discover_stats: dict, sync_stats: dict) -> str:
    """Return a plain-text IM summary (pipeline stats + priority counts).

    Does not send — callers use this to embed in markdown or other outputs.
    """
    total_merged = discover_stats.get("total_merged", 0)
    total_passed = discover_stats.get("total_passed", 0)
    written = discover_stats.get("written", 0)
    prio = discover_stats.get("priority", {})
    p0 = prio.get("P0", 0)
    p1 = prio.get("P1", 0)
    p2 = prio.get("P2", 0)
    s_errors = sync_stats.get("errors", 0)
    parts = [
        f"合并 {total_merged} 条 → 通过 {total_passed} 条 → 写入 {written} 条",
        f"P0={p0} P1={p1} P2={p2}",
    ]
    if s_errors:
        parts.append(f"飞书同步错误 {s_errors} 条")
    return " | ".join(parts)


def send_email(
    smtp_user: str,
    smtp_password: str,
    to: str,
    subject: str,
    body: str,
) -> bool:
    """Send an email via Gmail SMTP. Fallback — disabled by default, enable via secrets.feishu.gmail.enabled."""
    try:
        import smtplib
        from email.mime.text import MIMEText
    except ImportError:
        print("ERROR: smtplib not available", file=sys.stderr)
        return False

    if not smtp_password:
        print("WARNING: Gmail SMTP password not configured, skipping email", file=sys.stderr)
        return False

    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = smtp_user
        msg["To"] = to

        with smtplib.SMTP("smtp.gmail.com", 587, timeout=15) as s:
            s.starttls()
            s.login(smtp_user, smtp_password)
            s.send_message(msg)
        print("Gmail sent OK")
        return True
    except Exception as e:
        print(f"ERROR: Gmail send failed: {e}", file=sys.stderr)
        return False
