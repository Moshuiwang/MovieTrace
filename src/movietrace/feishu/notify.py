"""Feishu notification — send summary / alert messages via lark-cli, with Gmail stub."""

from __future__ import annotations

import json
import subprocess
import sys
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Shanghai")


def _lark(*args: str) -> dict:
    """Run a lark-cli command and return parsed JSON."""
    cmd = ["lark-cli", *args, "--as", "bot"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        raise RuntimeError(
            f"lark-cli failed (exit={result.returncode}):\n"
            f"cmd: {' '.join(cmd)}\n"
            f"stderr: {result.stderr[:500]}"
        )
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"_raw": result.stdout}


def send_text(user_open_id: str, text: str) -> bool:
    """Send a plain text message to a Feishu user via bot."""
    try:
        result = _lark(
            "im", "+messages-send",
            "--user-id", user_open_id,
            "--text", text,
        )
        ok = result.get("ok", False) if isinstance(result, dict) else False
        if not ok:
            print(f"WARNING: feishu message send returned ok=false: {result}", file=sys.stderr)
        return bool(ok)
    except Exception as e:
        print(f"ERROR: feishu message send failed: {e}", file=sys.stderr)
        return False


def send_summary(
    user_open_id: str,
    run_date: str,
    stats: dict,
    doc_url: str = "",
    log_file: str = "",
) -> bool:
    """Send a daily summary notification.

    stats should contain: total, created, updated, errors, and optionally
    new_discovery, new_season, p0_count, p1_count, p2_count, source_status.
    """
    total = stats.get("total", 0)
    created = stats.get("created", 0)
    updated = stats.get("updated", 0)
    errors = stats.get("errors", 0)
    parts = [f"MovieTrace 每日发现完成 - {run_date}", ""]
    parts.append(f"同步结果：{'成功' if errors == 0 else '部分成功'}")
    parts.append(f"同步条数：{total} (新增 {created}, 更新 {updated}, 错误 {errors})")

    nd = stats.get("new_discovery")
    ns = stats.get("new_season")
    if nd is not None or ns is not None:
        parts.append(f"新增发现：{nd or 0}")
        parts.append(f"新季更新：{ns or 0}")

    p0 = stats.get("p0_count")
    p1 = stats.get("p1_count")
    p2 = stats.get("p2_count")
    if p0 is not None:
        parts.append(f"优先级：P0={p0} / P1={p1 or 0} / P2={p2 or 0}")

    src = stats.get("source_status", "")
    if src:
        parts.append(f"数据源：{src}")

    if doc_url:
        parts.append(f"飞书文档：{doc_url}")
    if log_file:
        parts.append(f"本地日志：{log_file}")

    text = "\n".join(parts)
    return send_text(user_open_id, text)


def send_alert(
    user_open_id: str,
    level: str,
    title: str,
    detail: str = "",
    log_file: str = "",
) -> bool:
    """Send a failure/partial-success alert.

    level: 'error' or 'warning'.
    """
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
    return send_text(user_open_id, text)


# ── Gmail SMTP (stub) ─────────────────────────────────────────────────────

def send_email(
    smtp_user: str,
    smtp_password: str,
    to: str,
    subject: str,
    body: str,
) -> bool:
    """Send an email via Gmail SMTP. Stub — not yet configured."""
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
