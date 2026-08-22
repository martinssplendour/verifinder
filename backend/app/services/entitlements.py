from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from fastapi import Cookie, Response
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.billing_models import Profile, Subscription, SubscriptionTier, UsageEvent
from app.config import get_settings


COOKIE_NAME = "vf_subject"
COOKIE_MAX_AGE = 60 * 60 * 24 * 365
ASK_FREE_LIMIT_WORDS = 20
ASK_PAID_LIMIT_WORDS = 60
ASK_FREE_WINDOW = timedelta(days=1)
PLANNER_FREE_WINDOW = timedelta(days=7)
PAID_STATUSES = {"active", "trialing"}

# Development-only fallback. Production uses a stable secret supplied by Render.
_fallback_key = secrets.token_hex(32)


def _signing_key() -> bytes:
    configured = get_settings().subject_signing_key
    return (configured or _fallback_key).encode("utf-8")


def _sign(value: str) -> str:
    signature = hmac.new(_signing_key(), value.encode("utf-8"), hashlib.sha256).hexdigest()[:32]
    return f"{value}.{signature}"


def _verify(token: str) -> str | None:
    if "." not in token:
        return None
    value, _, signature = token.rpartition(".")
    expected = hmac.new(_signing_key(), value.encode("utf-8"), hashlib.sha256).hexdigest()[:32]
    if not hmac.compare_digest(signature, expected):
        return None
    return value


def resolve_subject_id(response: Response, vf_subject: str | None = Cookie(default=None)) -> str:
    verified = _verify(vf_subject) if vf_subject else None
    subject_id = verified or f"anon-{secrets.token_urlsafe(18)}"
    if verified is None:
        response.set_cookie(
            COOKIE_NAME,
            _sign(subject_id),
            max_age=COOKIE_MAX_AGE,
            httponly=True,
            secure=get_settings().environment == "production",
            samesite="lax",
        )
    return subject_id


@dataclass(frozen=True)
class EntitlementResult:
    allowed: bool
    tier: SubscriptionTier = SubscriptionTier.FREE
    code: str | None = None
    message: str | None = None
    reset_at: datetime | None = None


def get_or_create_profile(session: Session, subject_id: str, email: str | None = None) -> Profile:
    profile = session.get(Profile, subject_id)
    if profile is None:
        profile = Profile(id=subject_id, email=email, tier=SubscriptionTier.FREE)
        session.add(profile)
        session.commit()
    elif email and profile.email != email:
        profile.email = email
        profile.updated_at = datetime.now(timezone.utc)
        session.commit()
    return profile


def get_or_create_subscription(session: Session, user_id: str) -> Subscription:
    subscription = session.scalar(select(Subscription).where(Subscription.user_id == user_id))
    if subscription is None:
        subscription = Subscription(user_id=user_id, tier=SubscriptionTier.FREE)
        session.add(subscription)
        session.commit()
    return subscription


def effective_tier(session: Session, subject_id: str) -> SubscriptionTier:
    subscription = session.scalar(select(Subscription).where(Subscription.user_id == subject_id))
    if subscription and subscription.status in PAID_STATUSES:
        return subscription.tier
    # Compatibility for original profiles and local fixtures.
    profile = session.get(Profile, subject_id)
    if profile and profile.tier != SubscriptionTier.FREE and profile.subscription_status in (None, *PAID_STATUSES):
        return profile.tier
    return SubscriptionTier.FREE


def _usage_filter(
    subject_ids: tuple[str, ...], feature: str, since: datetime, network_hash: str | None
):
    identities = [UsageEvent.subject_id.in_(subject_ids)]
    if network_hash:
        identities.append(UsageEvent.network_hash == network_hash)
    return UsageEvent.feature == feature, UsageEvent.created_at >= since, or_(*identities)


def _recent_usage_count(
    session: Session,
    subject_id: str,
    feature: str,
    window: timedelta,
    *,
    subject_ids: tuple[str, ...] | None = None,
    network_hash: str | None = None,
) -> int:
    identities = subject_ids or (subject_id,)
    since = datetime.now(timezone.utc) - window
    return session.scalar(
        select(func.count()).select_from(UsageEvent).where(*_usage_filter(identities, feature, since, network_hash))
    ) or 0


def _first_recent_usage(
    session: Session,
    subject_ids: tuple[str, ...],
    feature: str,
    window: timedelta,
    network_hash: str | None,
) -> datetime | None:
    since = datetime.now(timezone.utc) - window
    return session.scalar(
        select(func.min(UsageEvent.created_at)).where(*_usage_filter(subject_ids, feature, since, network_hash))
    )


def record_usage(
    session: Session,
    subject_id: str,
    feature: str,
    detail: str | None = None,
    *,
    network_hash: str | None = None,
    quota_key: str | None = None,
) -> bool:
    session.add(
        UsageEvent(
            subject_id=subject_id,
            feature=feature,
            detail=detail,
            network_hash=network_hash,
            quota_key=quota_key,
        )
    )
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        return False
    return True


def check_ask_entitlement(
    session: Session,
    subject_id: str,
    question: str,
    *,
    subject_ids: tuple[str, ...] | None = None,
    network_hash: str | None = None,
) -> EntitlementResult:
    tier = effective_tier(session, subject_id)
    if tier != SubscriptionTier.FREE:
        word_count = len(question.split())
        if word_count > ASK_PAID_LIMIT_WORDS:
            return EntitlementResult(
                allowed=False,
                tier=tier,
                code="ask_word_limit",
                message=f"Ask VeriFinder accepts up to {ASK_PAID_LIMIT_WORDS} words per question (this one is {word_count}).",
            )
        return EntitlementResult(allowed=True, tier=tier)
    word_count = len(question.split())
    if word_count > ASK_FREE_LIMIT_WORDS:
        return EntitlementResult(
            allowed=False,
            code="ask_word_limit",
            message=f"Free questions are limited to {ASK_FREE_LIMIT_WORDS} words (this one is {word_count}). Upgrade to Plus for longer questions.",
        )
    identities = subject_ids or (subject_id,)
    first = _first_recent_usage(session, identities, "ask", ASK_FREE_WINDOW, network_hash)
    if first:
        return EntitlementResult(
            allowed=False,
            code="ask_daily_limit",
            message="You've used today's free question. Upgrade to Plus for unlimited questions, or try again tomorrow.",
            reset_at=first + ASK_FREE_WINDOW,
        )
    return EntitlementResult(allowed=True)


def check_planner_entitlement(
    session: Session,
    subject_id: str,
    *,
    subject_ids: tuple[str, ...] | None = None,
    network_hash: str | None = None,
) -> EntitlementResult:
    tier = effective_tier(session, subject_id)
    if tier != SubscriptionTier.FREE:
        return EntitlementResult(allowed=True, tier=tier)
    identities = subject_ids or (subject_id,)
    first = _first_recent_usage(session, identities, "planner", PLANNER_FREE_WINDOW, network_hash)
    if first:
        return EntitlementResult(
            allowed=False,
            code="planner_weekly_limit",
            message="You've used this week's free plan. Upgrade to Plus for unlimited plans, or try again next week.",
            reset_at=first + PLANNER_FREE_WINDOW,
        )
    return EntitlementResult(allowed=True)


def check_report_entitlement(session: Session, subject_id: str) -> EntitlementResult:
    tier = effective_tier(session, subject_id)
    if tier != SubscriptionTier.FREE:
        return EntitlementResult(allowed=True, tier=tier)
    return EntitlementResult(
        allowed=False,
        code="report_upgrade_required",
        message="PDF reports are available with Plus or Professional, or as a £4.99 single report.",
    )


def check_watchlist_entitlement(session: Session, subject_id: str) -> EntitlementResult:
    tier = effective_tier(session, subject_id)
    if tier != SubscriptionTier.FREE:
        return EntitlementResult(allowed=True, tier=tier)
    return EntitlementResult(
        allowed=False,
        code="watchlist_upgrade_required",
        message="Saved watchlists and change alerts are included with Plus and Professional.",
    )


def reserve_ask(
    session: Session,
    subject_id: str,
    question: str,
    *,
    subject_ids: tuple[str, ...] | None = None,
    network_hash: str | None = None,
) -> EntitlementResult:
    result = check_ask_entitlement(
        session, subject_id, question, subject_ids=subject_ids, network_hash=network_hash
    )
    if not result.allowed:
        return result
    now = datetime.now(timezone.utc)
    quota_key = None if result.tier != SubscriptionTier.FREE else f"ask:{subject_id}:{now.date().isoformat()}"
    if not record_usage(session, subject_id, "ask", network_hash=network_hash, quota_key=quota_key):
        return EntitlementResult(False, code="ask_daily_limit", message="You've used today's free question.")
    return result


def reserve_planner(
    session: Session,
    subject_id: str,
    *,
    subject_ids: tuple[str, ...] | None = None,
    network_hash: str | None = None,
) -> EntitlementResult:
    result = check_planner_entitlement(
        session, subject_id, subject_ids=subject_ids, network_hash=network_hash
    )
    if not result.allowed:
        return result
    now = datetime.now(timezone.utc)
    iso_year, iso_week, _ = now.isocalendar()
    quota_key = None if result.tier != SubscriptionTier.FREE else f"planner:{subject_id}:{iso_year}-W{iso_week:02d}"
    if not record_usage(session, subject_id, "planner", network_hash=network_hash, quota_key=quota_key):
        return EntitlementResult(False, code="planner_weekly_limit", message="You've used this week's free plan.")
    return result


def entitlement_snapshot(
    session: Session,
    subject_id: str,
    *,
    subject_ids: tuple[str, ...] | None = None,
    network_hash: str | None = None,
) -> dict[str, object]:
    identities = subject_ids or (subject_id,)
    tier = effective_tier(session, subject_id)
    paid = tier != SubscriptionTier.FREE
    ask_first = None if paid else _first_recent_usage(session, identities, "ask", ASK_FREE_WINDOW, network_hash)
    planner_first = None if paid else _first_recent_usage(
        session, identities, "planner", PLANNER_FREE_WINDOW, network_hash
    )
    return {
        "tier": tier.value,
        "ask": {
            "allowed": paid or ask_first is None,
            "word_limit": ASK_PAID_LIMIT_WORDS if paid else ASK_FREE_LIMIT_WORDS,
            "reset_at": ask_first + ASK_FREE_WINDOW if ask_first else None,
        },
        "planner": {
            "allowed": paid or planner_first is None,
            "reset_at": planner_first + PLANNER_FREE_WINDOW if planner_first else None,
        },
        "report_download": {"allowed": paid},
        "watchlists": {"allowed": paid},
    }
