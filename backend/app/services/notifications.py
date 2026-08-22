from __future__ import annotations

import html
import json
from email.utils import parseaddr
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.billing_models import Profile, WatchlistAlert, WatchlistEntry
from app.config import get_settings

MCP_PROTOCOL_VERSION = "2025-03-26"


def _email_provider() -> str | None:
    settings = get_settings()
    provider = settings.email_provider.strip().lower()
    if provider == "zoho_mcp":
        return provider if settings.zoho_mcp_url and settings.zoho_mail_account_id else None
    if provider == "resend":
        return provider if settings.email_api_key else None
    if provider != "auto":
        return None
    if settings.zoho_mcp_url and settings.zoho_mail_account_id:
        return "zoho_mcp"
    if settings.email_api_key:
        return "resend"
    return None


def email_configured() -> bool:
    return _email_provider() is not None


def _mcp_response_payload(response: httpx.Response) -> dict[str, Any]:
    response.raise_for_status()
    if response.headers.get("content-type", "").lower().startswith("application/json"):
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("Zoho MCP returned an invalid JSON response.")
        return payload
    for line in response.text.splitlines():
        if line.startswith("data:"):
            payload = json.loads(line[5:].strip())
            if isinstance(payload, dict):
                return payload
    raise ValueError("Zoho MCP returned an invalid event stream.")


def _send_with_zoho_mcp(*, to_address: str, subject: str, html_content: str) -> None:
    settings = get_settings()
    if not settings.zoho_mcp_url or not settings.zoho_mail_account_id:
        raise RuntimeError("Zoho MCP is not configured.")
    from_address = parseaddr(settings.notification_from_email)[1]
    if not from_address:
        raise RuntimeError("Notification sender address is invalid.")
    headers = {
        "Accept": "application/json, text/event-stream",
        "MCP-Protocol-Version": MCP_PROTOCOL_VERSION,
    }
    with httpx.Client(timeout=12.0) as client:
        initialize_response = client.post(
            settings.zoho_mcp_url,
            headers=headers,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": MCP_PROTOCOL_VERSION,
                    "capabilities": {},
                    "clientInfo": {"name": "verifinder", "version": "1.0"},
                },
            },
        )
        initialize_payload = _mcp_response_payload(initialize_response)
        if initialize_payload.get("error"):
            raise RuntimeError("Zoho MCP initialization failed.")
        session_id = initialize_response.headers.get("mcp-session-id")
        if session_id:
            headers["Mcp-Session-Id"] = session_id
        initialized_response = client.post(
            settings.zoho_mcp_url,
            headers=headers,
            json={"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
        )
        initialized_response.raise_for_status()
        send_response = client.post(
            settings.zoho_mcp_url,
            headers=headers,
            json={
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "ZohoMail_sendEmail",
                    "arguments": {
                        "body": {
                            "fromAddress": from_address,
                            "toAddress": to_address,
                            "subject": subject,
                            "content": html_content,
                            "mailFormat": "html",
                            "encoding": "UTF-8",
                            "askReceipt": "no",
                        },
                        "path_variables": {"accountId": settings.zoho_mail_account_id},
                    },
                },
            },
        )
        send_payload = _mcp_response_payload(send_response)
        result = send_payload.get("result") or {}
        structured_content = result.get("structuredContent") or {}
        if send_payload.get("error") or result.get("isError") or structured_content.get("status") == "failure":
            raise RuntimeError("Zoho MCP email delivery failed.")


def _send_with_resend(*, to_address: str, subject: str, text_content: str, html_content: str) -> None:
    settings = get_settings()
    if not settings.email_api_key:
        raise RuntimeError("Resend is not configured.")
    response = httpx.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {settings.email_api_key}", "Content-Type": "application/json"},
        json={
            "from": settings.notification_from_email,
            "to": [to_address],
            "subject": subject,
            "text": text_content,
            "html": html_content,
        },
        timeout=12.0,
    )
    response.raise_for_status()


def dispatch_alert_email(billing_session: Session, alert: WatchlistAlert) -> None:
    entry = billing_session.get(WatchlistEntry, alert.watchlist_entry_id)
    if entry is None or not entry.notifications_enabled:
        alert.email_status = "skipped_disabled"
        billing_session.commit()
        return
    profile = billing_session.get(Profile, alert.subject_id)
    if profile is None or not profile.email:
        alert.email_status = "skipped_no_email"
        billing_session.commit()
        return
    provider = _email_provider()
    if provider is None:
        alert.email_status = "pending_provider"
        billing_session.commit()
        return
    settings = get_settings()
    subject = f"VeriFinder change alert: {entry.label or entry.entity_id}"
    text_content = f"{alert.summary}\n\nReview your watchlist: {settings.app_url.rstrip('/')}/?account=watchlist"
    html_content = (
        "<h2>VeriFinder change alert</h2>"
        f"<p>{html.escape(alert.summary)}</p>"
        f"<p><a href='{html.escape(settings.app_url.rstrip('/'))}/?account=watchlist'>Review your watchlist</a></p>"
        "<p><small>Public records can change. Open the official source before acting.</small></p>"
    )
    try:
        if provider == "zoho_mcp":
            _send_with_zoho_mcp(to_address=profile.email, subject=subject, html_content=html_content)
        else:
            _send_with_resend(
                to_address=profile.email,
                subject=subject,
                text_content=text_content,
                html_content=html_content,
            )
        alert.email_status = "sent"
        alert.email_error = None
    except (httpx.HTTPError, ValueError, RuntimeError) as error:
        alert.email_status = "failed"
        if isinstance(error, httpx.HTTPStatusError):
            alert.email_error = f"Email provider returned {error.response.status_code}."
        else:
            alert.email_error = "Email provider request failed."
    billing_session.commit()


def retry_pending_alerts(billing_session: Session, limit: int = 100) -> dict[str, int]:
    alerts = list(
        billing_session.scalars(
            select(WatchlistAlert)
            .where(WatchlistAlert.email_status.in_(["pending", "pending_provider", "failed"]))
            .order_by(WatchlistAlert.created_at.asc())
            .limit(limit)
        )
    )
    for alert in alerts:
        dispatch_alert_email(billing_session, alert)
    return {
        "attempted": len(alerts),
        "sent": sum(alert.email_status == "sent" for alert in alerts),
        "failed": sum(alert.email_status == "failed" for alert in alerts),
    }
