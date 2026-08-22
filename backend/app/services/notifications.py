from __future__ import annotations

import html

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.billing_models import Profile, WatchlistAlert, WatchlistEntry
from app.config import get_settings


def email_configured() -> bool:
    return bool(get_settings().email_api_key)


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
    settings = get_settings()
    if not settings.email_api_key:
        alert.email_status = "pending_provider"
        billing_session.commit()
        return
    try:
        response = httpx.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {settings.email_api_key}", "Content-Type": "application/json"},
            json={
                "from": settings.notification_from_email,
                "to": [profile.email],
                "subject": f"VeriFinder change alert: {entry.label or entry.entity_id}",
                "text": f"{alert.summary}\n\nReview your watchlist: {settings.app_url.rstrip('/')}/?account=watchlist",
                "html": (
                    "<h2>VeriFinder change alert</h2>"
                    f"<p>{html.escape(alert.summary)}</p>"
                    f"<p><a href='{html.escape(settings.app_url.rstrip('/'))}/?account=watchlist'>Review your watchlist</a></p>"
                    "<p><small>Public records can change. Open the official source before acting.</small></p>"
                ),
            },
            timeout=12.0,
        )
        if response.status_code not in {200, 201, 202}:
            alert.email_status = "failed"
            alert.email_error = f"Email provider returned {response.status_code}."
        else:
            alert.email_status = "sent"
            alert.email_error = None
    except httpx.HTTPError as error:
        alert.email_status = "failed"
        alert.email_error = str(error)[:500]
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
