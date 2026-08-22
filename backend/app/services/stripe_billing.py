from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import stripe
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.billing_models import Profile, StripeEvent, Subscription, SubscriptionTier
from app.config import get_settings
from app.services.entitlements import credit_coins, get_or_create_profile, get_or_create_subscription


ACTIVE_STATUSES = {"active", "trialing"}


class BillingConfigurationError(RuntimeError):
    pass


def _stripe_key() -> str:
    key = get_settings().stripe_secret_key
    if not key:
        raise BillingConfigurationError("Stripe billing is not configured.")
    return key


def billing_configured() -> bool:
    settings = get_settings()
    return bool(
        settings.stripe_secret_key
        and settings.stripe_webhook_secret
        and settings.stripe_plus_price_id
        and settings.stripe_plus_annual_price_id
        and settings.stripe_professional_price_id
        and settings.stripe_professional_annual_price_id
    )


def coin_billing_configured() -> bool:
    settings = get_settings()
    return bool(
        settings.stripe_secret_key
        and settings.stripe_webhook_secret
        and (settings.stripe_coin_pack_25_price_id or settings.stripe_coin_pack_5_price_id)
        and (settings.stripe_coin_pack_75_price_id or settings.stripe_coin_pack_15_price_id)
    )


def _coin_pack(pack: str) -> tuple[str, int]:
    settings = get_settings()
    packs = {
        "coins_25": (
            settings.stripe_coin_pack_25_price_id or settings.stripe_coin_pack_5_price_id,
            25,
        ),
        "coins_75": (
            settings.stripe_coin_pack_75_price_id or settings.stripe_coin_pack_15_price_id,
            75,
        ),
    }
    price_id, coins = packs.get(pack, (None, 0))
    if not price_id:
        raise BillingConfigurationError(f"The {pack} Stripe price is not configured.")
    return price_id, coins


def _price_for_tier(tier: SubscriptionTier, cadence: str = "monthly") -> str:
    settings = get_settings()
    prices = {
        (SubscriptionTier.PLUS, "monthly"): settings.stripe_plus_price_id,
        (SubscriptionTier.PLUS, "annual"): settings.stripe_plus_annual_price_id,
        (SubscriptionTier.PROFESSIONAL, "monthly"): settings.stripe_professional_price_id,
        (SubscriptionTier.PROFESSIONAL, "annual"): settings.stripe_professional_annual_price_id,
    }
    price_id = prices.get((tier, cadence))
    if not price_id:
        raise BillingConfigurationError(f"The {tier.value} Stripe price is not configured.")
    return price_id


def _tier_for_price(price_id: str | None) -> SubscriptionTier:
    settings = get_settings()
    if price_id and price_id in {settings.stripe_professional_price_id, settings.stripe_professional_annual_price_id}:
        return SubscriptionTier.PROFESSIONAL
    if price_id and price_id in {settings.stripe_plus_price_id, settings.stripe_plus_annual_price_id}:
        return SubscriptionTier.PLUS
    return SubscriptionTier.FREE


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if hasattr(value, "to_dict_recursive"):
        return value.to_dict_recursive()
    if hasattr(value, "to_dict"):
        return value.to_dict()
    return dict(value)


def _timestamp(value: object) -> datetime | None:
    if not isinstance(value, (int, float)):
        return None
    return datetime.fromtimestamp(value, tz=timezone.utc)


def _subscription_price(payload: dict[str, Any]) -> str | None:
    items = payload.get("items") or {}
    data = items.get("data") if isinstance(items, dict) else None
    if not isinstance(data, list) or not data:
        return None
    price = data[0].get("price") if isinstance(data[0], dict) else None
    return price.get("id") if isinstance(price, dict) else None


def _subscription_period_end(payload: dict[str, Any]) -> datetime | None:
    direct = _timestamp(payload.get("current_period_end"))
    if direct:
        return direct
    items = payload.get("items") or {}
    data = items.get("data") if isinstance(items, dict) else None
    if isinstance(data, list) and data and isinstance(data[0], dict):
        return _timestamp(data[0].get("current_period_end"))
    return None


def create_checkout_session(
    session: Session, user_id: str, email: str | None, tier: SubscriptionTier, cadence: str = "monthly"
) -> str:
    if tier not in {SubscriptionTier.PLUS, SubscriptionTier.PROFESSIONAL}:
        raise ValueError("Checkout is only available for paid tiers.")
    profile = get_or_create_profile(session, user_id, email)
    subscription = get_or_create_subscription(session, user_id)
    if not subscription.customer_id:
        customer = stripe.Customer.create(
            api_key=_stripe_key(),
            email=email,
            metadata={"verifinder_user_id": user_id},
        )
        subscription.customer_id = customer.id
        profile.stripe_customer_id = customer.id
        session.commit()
    settings = get_settings()
    checkout = stripe.checkout.Session.create(
        api_key=_stripe_key(),
        mode="subscription",
        customer=subscription.customer_id,
        line_items=[{"price": _price_for_tier(tier, cadence), "quantity": 1}],
        allow_promotion_codes=True,
        client_reference_id=user_id,
        metadata={"verifinder_user_id": user_id, "tier": tier.value, "cadence": cadence},
        subscription_data={"metadata": {"verifinder_user_id": user_id, "tier": tier.value, "cadence": cadence}},
        success_url=f"{settings.app_url.rstrip('/')}?billing=success",
        cancel_url=f"{settings.app_url.rstrip('/')}?billing=cancelled",
    )
    if not checkout.url:
        raise RuntimeError("Stripe did not return a checkout URL.")
    return checkout.url


def create_coin_checkout_session(
    session: Session,
    user_id: str,
    email: str | None,
    pack: str,
) -> str:
    profile = get_or_create_profile(session, user_id, email)
    subscription = get_or_create_subscription(session, user_id)
    if not subscription.customer_id:
        customer = stripe.Customer.create(
            api_key=_stripe_key(),
            email=email,
            metadata={"verifinder_user_id": user_id},
        )
        subscription.customer_id = customer.id
        profile.stripe_customer_id = customer.id
        session.commit()
    price_id, coins = _coin_pack(pack)
    settings = get_settings()
    metadata = {
        "verifinder_user_id": user_id,
        "purchase_type": "ask_coins",
        "coin_pack": pack,
        "coins": str(coins),
    }
    checkout = stripe.checkout.Session.create(
        api_key=_stripe_key(),
        mode="payment",
        customer=subscription.customer_id,
        payment_method_types=["card"],
        line_items=[{"price": price_id, "quantity": 1}],
        client_reference_id=user_id,
        metadata=metadata,
        payment_intent_data={"metadata": metadata},
        success_url=f"{settings.app_url.rstrip('/')}/ask?coins=success",
        cancel_url=f"{settings.app_url.rstrip('/')}/ask?coins=cancelled",
    )
    if not checkout.url:
        raise RuntimeError("Stripe did not return a checkout URL.")
    return checkout.url


def create_portal_session(session: Session, user_id: str) -> str:
    subscription = session.scalar(select(Subscription).where(Subscription.user_id == user_id))
    if not subscription or not subscription.customer_id:
        raise LookupError("No Stripe customer exists for this account.")
    settings = get_settings()
    arguments: dict[str, object] = {
        "api_key": _stripe_key(),
        "customer": subscription.customer_id,
        "return_url": f"{settings.app_url.rstrip('/')}?billing=return",
    }
    if settings.stripe_portal_configuration_id:
        arguments["configuration"] = settings.stripe_portal_configuration_id
    portal = stripe.billing_portal.Session.create(**arguments)
    return portal.url


def _find_subscription(session: Session, payload: dict[str, Any]) -> Subscription | None:
    metadata = payload.get("metadata") or {}
    user_id = metadata.get("verifinder_user_id") if isinstance(metadata, dict) else None
    if user_id:
        profile = session.get(Profile, str(user_id))
        if not profile:
            profile = Profile(id=str(user_id), tier=SubscriptionTier.FREE)
            session.add(profile)
            session.flush()
        subscription = session.scalar(select(Subscription).where(Subscription.user_id == str(user_id)))
        if not subscription:
            subscription = Subscription(user_id=str(user_id), tier=SubscriptionTier.FREE)
            session.add(subscription)
            session.flush()
        return subscription
    customer_id = payload.get("customer")
    subscription_id = payload.get("id")
    return session.scalar(
        select(Subscription).where(
            or_(
                Subscription.customer_id == str(customer_id) if customer_id else False,
                Subscription.subscription_id == str(subscription_id) if subscription_id else False,
            )
        )
    )


def _sync_subscription(session: Session, raw_payload: Any) -> None:
    payload = _as_dict(raw_payload)
    subscription = _find_subscription(session, payload)
    if not subscription:
        return
    price_id = _subscription_price(payload)
    status = str(payload.get("status") or "unknown")
    subscription.customer_id = str(payload.get("customer")) if payload.get("customer") else subscription.customer_id
    subscription.subscription_id = str(payload.get("id")) if payload.get("id") else subscription.subscription_id
    subscription.status = status
    subscription.price_id = price_id
    subscription.tier = _tier_for_price(price_id) if status in ACTIVE_STATUSES else SubscriptionTier.FREE
    subscription.current_period_end = _subscription_period_end(payload)
    subscription.cancel_at_period_end = bool(payload.get("cancel_at_period_end", False))
    subscription.updated_at = datetime.now(timezone.utc)

    profile = session.get(Profile, subscription.user_id)
    if profile:
        profile.tier = subscription.tier
        profile.stripe_customer_id = subscription.customer_id
        profile.stripe_subscription_id = subscription.subscription_id
        profile.subscription_status = subscription.status
        profile.subscription_current_period_end = subscription.current_period_end
        profile.updated_at = datetime.now(timezone.utc)


def _credit_coin_checkout(session: Session, raw_payload: Any) -> bool:
    checkout = _as_dict(raw_payload)
    if checkout.get("payment_status") != "paid":
        return False
    metadata = checkout.get("metadata") or {}
    if not isinstance(metadata, dict) or metadata.get("purchase_type") != "ask_coins":
        return False
    user_id = str(metadata.get("verifinder_user_id") or "").strip()
    pack = str(metadata.get("coin_pack") or "").strip()
    checkout_id = str(checkout.get("id") or "").strip()
    if not user_id or not checkout_id:
        return False
    _, coins = _coin_pack(pack)
    profile = session.get(Profile, user_id)
    if profile is None:
        profile = Profile(id=user_id, tier=SubscriptionTier.FREE)
        session.add(profile)
        session.flush()
    customer_id = checkout.get("customer")
    if customer_id and not profile.stripe_customer_id:
        profile.stripe_customer_id = str(customer_id)
    return credit_coins(
        session,
        user_id,
        coins,
        f"stripe-checkout:{checkout_id}",
        detail={"checkout_session_id": checkout_id, "coin_pack": pack},
    )


def process_webhook(session: Session, payload: bytes, signature: str) -> bool:
    settings = get_settings()
    if not settings.stripe_webhook_secret:
        raise BillingConfigurationError("The Stripe webhook secret is not configured.")
    event = stripe.Webhook.construct_event(payload, signature, settings.stripe_webhook_secret)
    event_id = str(event["id"])
    event_type = str(event["type"])
    session.add(StripeEvent(event_id=event_id, event_type=event_type))
    try:
        session.flush()
    except IntegrityError:
        session.rollback()
        return False

    event_object = event["data"]["object"]
    if event_type in {"checkout.session.completed", "checkout.session.async_payment_succeeded"}:
        checkout = _as_dict(event_object)
        subscription_id = None
        if checkout.get("mode") == "payment":
            _credit_coin_checkout(session, checkout)
        else:
            subscription_id = checkout.get("subscription")
        if checkout.get("mode") != "payment" and subscription_id:
            remote = stripe.Subscription.retrieve(str(subscription_id), api_key=_stripe_key())
            _sync_subscription(session, remote)
    elif event_type in {
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
    }:
        _sync_subscription(session, event_object)
    elif event_type == "invoice.payment_failed":
        invoice = _as_dict(event_object)
        subscription_details = invoice.get("parent", {}).get("subscription_details", {}) if isinstance(invoice.get("parent"), dict) else {}
        subscription_id = invoice.get("subscription") or subscription_details.get("subscription")
        if subscription_id:
            local = session.scalar(
                select(Subscription).where(Subscription.subscription_id == str(subscription_id))
            )
            if local:
                local.status = "past_due"
                local.tier = SubscriptionTier.FREE
                local.updated_at = datetime.now(timezone.utc)
    session.commit()
    return True
