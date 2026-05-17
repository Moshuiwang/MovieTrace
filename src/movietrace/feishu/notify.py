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
    """Send a text message via /im/v1/messages, return parsed response.

    receive_id_type: 'open_id' (user) or 'chat_id' (group)
    """
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
    """Send a plain text message to a Feishu user or group.

    receive_id_type: 'open_id' for user, 'chat_id' for group
    """
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
    """Send a daily summary notification.

    receive_id_type: 'open_id' for user, 'chat_id' for group
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
    """Send a failure/partial-success alert.

    level: 'error' or 'warning'.
    receive_id_type: 'open_id' for user, 'chat_id' for group
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
    return send_text(receive_id, text, app_id=app_id, app_secret=app_secret, receive_id_type=receive_id_type)


# ── Gmail SMTP (stub) ─────────────────────────────────────────────────────

def send_email(
    smtp_user: str,
    smtp_password: str,
    to: str,
    subject: str,
    body: str,
) -> bool:
    """Send an email via Gmail SMTP. Fallback path — disabled by default, enable via secrets.feishu.gmail.enabled."""
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
