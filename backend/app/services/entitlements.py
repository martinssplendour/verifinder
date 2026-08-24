from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from fastapi import Cookie, Response
from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.billing_models import (
    CoinTransaction,
    CoinWallet,
    Profile,
    Subscription,
    SubscriptionTier,
    UsageEvent,
)
from app.config import get_settings
from app.services.admin_access import active_admin_grant


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
    payment_required: bool = False
    sign_in_required: bool = False
    coin_balance: int = 0
    coin_reservation_id: str | None = None


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


def coin_balance(session: Session, subject_id: str) -> int:
    wallet = session.get(CoinWallet, subject_id)
    return max(0, wallet.balance) if wallet else 0


def credit_coins(
    session: Session,
    subject_id: str,
    amount: int,
    reference_id: str,
    *,
    detail: dict | None = None,
) -> bool:
    """Credit a purchase inside the caller's transaction, once per reference."""
    if amount <= 0:
        raise ValueError("Coin credits must be positive.")
    existing = session.scalar(
        select(CoinTransaction.id).where(CoinTransaction.reference_id == reference_id)
    )
    if existing:
        return False
    wallet = session.get(CoinWallet, subject_id)
    if wallet is None:
        wallet = CoinWallet(subject_id=subject_id, balance=0)
        session.add(wallet)
        session.flush()
    wallet.balance += amount
    wallet.updated_at = datetime.now(timezone.utc)
    session.add(
        CoinTransaction(
            subject_id=subject_id,
            delta=amount,
            reason="purchase",
            reference_id=reference_id,
            balance_after=wallet.balance,
            detail=detail,
        )
    )
    session.flush()
    return True


def refund_ask_coin(session: Session, subject_id: str, reservation_id: str | None) -> bool:
    """Return a reserved coin after answer generation fails; safe to retry."""
    if not reservation_id:
        return False
    debit_reference = f"ask:{reservation_id}"
    refund_reference = f"ask-refund:{reservation_id}"
    debit = session.scalar(
        select(CoinTransaction).where(
            CoinTransaction.subject_id == subject_id,
            CoinTransaction.reference_id == debit_reference,
            CoinTransaction.delta == -1,
        )
    )
    refunded = session.scalar(
        select(CoinTransaction.id).where(CoinTransaction.reference_id == refund_reference)
    )
    if not debit or refunded:
        return False
    wallet = session.get(CoinWallet, subject_id)
    if wallet is None:
        wallet = CoinWallet(subject_id=subject_id, balance=0)
        session.add(wallet)
        session.flush()
    wallet.balance += 1
    wallet.updated_at = datetime.now(timezone.utc)
    session.add(
        CoinTransaction(
            subject_id=subject_id,
            delta=1,
            reason="ask_refund",
            reference_id=refund_reference,
            balance_after=wallet.balance,
            detail={"debit_reference": debit_reference},
        )
    )
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        return False
    return True


def get_or_create_subscription(session: Session, user_id: str) -> Subscription:
    subscription = session.scalar(select(Subscription).where(Subscription.user_id == user_id))
    if subscription is None:
        subscription = Subscription(user_id=user_id, tier=SubscriptionTier.FREE)
        session.add(subscription)
        session.commit()
    return subscription


def _subscription_tier(session: Session, subject_id: str) -> SubscriptionTier:
    subscription = session.scalar(select(Subscription).where(Subscription.user_id == subject_id))
    if subscription and subscription.status in PAID_STATUSES:
        return subscription.tier
    # Compatibility for original profiles and local fixtures.
    profile = session.get(Profile, subject_id)
    if profile and profile.tier != SubscriptionTier.FREE and profile.subscription_status in (None, *PAID_STATUSES):
        return profile.tier
    return SubscriptionTier.FREE


def has_unrestricted_admin_access(
    session: Session,
    subject_id: str,
    email: str | None = None,
) -> bool:
    resolved_email = email
    if not resolved_email:
        profile = session.get(Profile, subject_id)
        resolved_email = profile.email if profile else None
    return active_admin_grant(session, resolved_email) is not None


def effective_tier(
    session: Session,
    subject_id: str,
    email: str | None = None,
) -> SubscriptionTier:
    if has_unrestricted_admin_access(session, subject_id, email):
        return SubscriptionTier.PROFESSIONAL
    return _subscription_tier(session, subject_id)


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
    authenticated: bool = False,
    email: str | None = None,
) -> EntitlementResult:
    admin = has_unrestricted_admin_access(session, subject_id, email)
    tier = SubscriptionTier.PROFESSIONAL if admin else _subscription_tier(session, subject_id)
    word_count = len(question.split())
    if admin:
        return EntitlementResult(allowed=True, tier=tier)
    if tier != SubscriptionTier.FREE:
        if word_count > ASK_PAID_LIMIT_WORDS:
            return EntitlementResult(
                allowed=False,
                tier=tier,
                code="ask_word_limit",
                message=f"Ask VeriFinder accepts up to {ASK_PAID_LIMIT_WORDS} words per question (this one is {word_count}).",
            )
        return EntitlementResult(allowed=True, tier=tier)
    if word_count > ASK_PAID_LIMIT_WORDS:
        return EntitlementResult(
            allowed=False,
            code="ask_word_limit",
            message=f"Ask VeriFinder accepts up to {ASK_PAID_LIMIT_WORDS} words per message (this one is {word_count}).",
        )
    identities = subject_ids or (subject_id,)
    first = _first_recent_usage(session, identities, "ask", ASK_FREE_WINDOW, network_hash)
    needs_coin = word_count > ASK_FREE_LIMIT_WORDS or first is not None
    if not needs_coin:
        return EntitlementResult(allowed=True)
    balance = coin_balance(session, subject_id) if authenticated else 0
    if authenticated and balance > 0:
        return EntitlementResult(allowed=True, coin_balance=balance)
    if not authenticated:
        reason = (
            f"Free questions are limited to {ASK_FREE_LIMIT_WORDS} words."
            if word_count > ASK_FREE_LIMIT_WORDS
            else "You've used today's free question."
        )
        return EntitlementResult(
            allowed=False,
            code="ask_sign_in_required",
            message=f"{reason} Sign in to buy coins for follow-up messages or choose Plus.",
            reset_at=first + ASK_FREE_WINDOW if first else None,
            payment_required=True,
            sign_in_required=True,
        )
    return EntitlementResult(
        allowed=False,
        code="ask_coins_required",
        message="Your free question has been used. Buy coins for occasional follow-ups or choose Plus for unlimited Ask.",
        reset_at=first + ASK_FREE_WINDOW if first else None,
        payment_required=True,
        coin_balance=balance,
    )


def check_planner_entitlement(
    session: Session,
    subject_id: str,
    *,
    subject_ids: tuple[str, ...] | None = None,
    network_hash: str | None = None,
    email: str | None = None,
) -> EntitlementResult:
    tier = effective_tier(session, subject_id, email)
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


def check_report_entitlement(
    session: Session,
    subject_id: str,
    email: str | None = None,
) -> EntitlementResult:
    tier = effective_tier(session, subject_id, email)
    if tier != SubscriptionTier.FREE:
        return EntitlementResult(allowed=True, tier=tier)
    return EntitlementResult(
        allowed=False,
        code="report_upgrade_required",
        message="PDF reports are available with Plus or Professional, or as a £4.99 single report.",
    )


def check_watchlist_entitlement(
    session: Session,
    subject_id: str,
    email: str | None = None,
) -> EntitlementResult:
    tier = effective_tier(session, subject_id, email)
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
    authenticated: bool = False,
    email: str | None = None,
) -> EntitlementResult:
    result = check_ask_entitlement(
        session,
        subject_id,
        question,
        subject_ids=subject_ids,
        network_hash=network_hash,
        authenticated=authenticated,
        email=email,
    )
    if not result.allowed:
        return result
    now = datetime.now(timezone.utc)
    identities = subject_ids or (subject_id,)
    uses_free_allowance = (
        result.tier == SubscriptionTier.FREE
        and len(question.split()) <= ASK_FREE_LIMIT_WORDS
        and _first_recent_usage(session, identities, "ask", ASK_FREE_WINDOW, network_hash) is None
    )
    reservation_id: str | None = None
    if result.tier == SubscriptionTier.FREE and not uses_free_allowance:
        reservation_id = str(uuid.uuid4())
        debit = session.execute(
            update(CoinWallet)
            .where(CoinWallet.subject_id == subject_id, CoinWallet.balance > 0)
            .values(balance=CoinWallet.balance - 1, updated_at=now)
        )
        if debit.rowcount != 1:
            session.rollback()
            return EntitlementResult(
                False,
                code="ask_coins_required",
                message="Your coin balance changed before this message was sent. Top up to continue.",
                payment_required=True,
                coin_balance=coin_balance(session, subject_id),
            )
        balance_after = coin_balance(session, subject_id)
        session.add(
            CoinTransaction(
                subject_id=subject_id,
                delta=-1,
                reason="ask",
                reference_id=f"ask:{reservation_id}",
                balance_after=balance_after,
                detail={"question_words": len(question.split())},
            )
        )
        quota_key = None
        usage_feature = "ask_coin"
    else:
        quota_key = (
            f"ask:{subject_id}:{now.date().isoformat()}"
            if result.tier == SubscriptionTier.FREE
            else None
        )
        usage_feature = "ask" if result.tier == SubscriptionTier.FREE else "ask_paid"
    session.add(
        UsageEvent(
            subject_id=subject_id,
            feature=usage_feature,
            network_hash=network_hash,
            quota_key=quota_key,
        )
    )
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        return EntitlementResult(
            False,
            code="ask_daily_limit",
            message="You've used today's free question. Buy coins to continue this conversation.",
            payment_required=authenticated,
            sign_in_required=not authenticated,
            coin_balance=coin_balance(session, subject_id) if authenticated else 0,
        )
    return EntitlementResult(
        allowed=True,
        tier=result.tier,
        coin_balance=coin_balance(session, subject_id) if authenticated else 0,
        coin_reservation_id=reservation_id,
    )


def reserve_planner(
    session: Session,
    subject_id: str,
    *,
    subject_ids: tuple[str, ...] | None = None,
    network_hash: str | None = None,
    email: str | None = None,
) -> EntitlementResult:
    result = check_planner_entitlement(
        session,
        subject_id,
        subject_ids=subject_ids,
        network_hash=network_hash,
        email=email,
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
    email: str | None = None,
) -> dict[str, object]:
    identities = subject_ids or (subject_id,)
    admin = has_unrestricted_admin_access(session, subject_id, email)
    tier = SubscriptionTier.PROFESSIONAL if admin else _subscription_tier(session, subject_id)
    paid = tier != SubscriptionTier.FREE
    balance = coin_balance(session, subject_id) if not subject_id.startswith("anon-") else 0
    ask_first = None if paid else _first_recent_usage(session, identities, "ask", ASK_FREE_WINDOW, network_hash)
    planner_first = None if paid else _first_recent_usage(
        session, identities, "planner", PLANNER_FREE_WINDOW, network_hash
    )
    return {
        "tier": tier.value,
        "ask": {
            "allowed": paid or balance > 0 or ask_first is None,
            "word_limit": None if admin else ASK_PAID_LIMIT_WORDS if paid or balance > 0 else ASK_FREE_LIMIT_WORDS,
            "reset_at": ask_first + ASK_FREE_WINDOW if ask_first else None,
        },
        "planner": {
            "allowed": paid or planner_first is None,
            "reset_at": planner_first + PLANNER_FREE_WINDOW if planner_first else None,
        },
        "report_download": {"allowed": paid},
        "watchlists": {"allowed": paid},
    }
