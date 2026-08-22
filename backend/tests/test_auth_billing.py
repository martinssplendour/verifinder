import asyncio
import hashlib
import hmac
import json
import time
from types import SimpleNamespace

from fastapi import Response
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.billing_models import BillingBase, CoinTransaction, CoinWallet, Profile, Subscription, SubscriptionTier
from app.config import get_settings
from app.services import auth
from app.services.entitlements import _sign
from app.services import stripe_billing
from app.services.stripe_billing import process_webhook


def billing_session() -> Session:
    engine = create_engine("sqlite://")
    BillingBase.metadata.create_all(engine)
    return Session(engine)


def test_authenticated_identity_preserves_anonymous_quota_alias(monkeypatch):
    async def verified(_token: str):
        return {"id": "00000000-0000-0000-0000-000000000001", "email": "person@example.com"}

    monkeypatch.setattr(auth, "_verify_supabase_token", verified)
    cookie = _sign("anon-existing")
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/api/account/me",
            "headers": [(b"cookie", f"vf_subject={cookie}".encode())],
            "client": ("203.0.113.8", 443),
        }
    )
    identity = asyncio.run(
        auth.resolve_identity(
            request,
            Response(),
            HTTPAuthorizationCredentials(scheme="Bearer", credentials="valid-token"),
        )
    )
    assert identity.authenticated is True
    assert identity.email == "person@example.com"
    assert identity.quota_subject_ids == (
        "00000000-0000-0000-0000-000000000001",
        "anon-existing",
    )
    assert identity.network_hash and "203.0.113.8" not in identity.network_hash


def test_stripe_webhook_sync_is_idempotent(monkeypatch):
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "test_webhook_signing_secret")
    monkeypatch.setenv("STRIPE_PLUS_PRICE_ID", "price_plus")
    monkeypatch.setenv("STRIPE_PROFESSIONAL_PRICE_ID", "price_pro")
    get_settings.cache_clear()
    session = billing_session()
    user_id = "00000000-0000-0000-0000-000000000002"
    session.add(Profile(id=user_id, email="billing@example.com", tier=SubscriptionTier.FREE))
    session.commit()

    event = {
        "id": "evt_verifinder_1",
        "object": "event",
        "type": "customer.subscription.updated",
        "data": {
            "object": {
                "id": "sub_verifinder_1",
                "object": "subscription",
                "customer": "cus_verifinder_1",
                "status": "active",
                "cancel_at_period_end": False,
                "current_period_end": int(time.time()) + 86400,
                "metadata": {"verifinder_user_id": user_id},
                "items": {"data": [{"price": {"id": "price_plus"}}]},
            }
        },
    }
    payload = json.dumps(event, separators=(",", ":")).encode()
    timestamp = int(time.time())
    digest = hmac.new(
        b"test_webhook_signing_secret", f"{timestamp}.{payload.decode()}".encode(), hashlib.sha256
    ).hexdigest()
    signature = f"t={timestamp},v1={digest}"

    assert process_webhook(session, payload, signature) is True
    subscription = session.query(Subscription).filter_by(user_id=user_id).one()
    assert subscription.tier == SubscriptionTier.PLUS
    assert subscription.status == "active"
    assert process_webhook(session, payload, signature) is False
    assert session.query(Subscription).count() == 1
    get_settings.cache_clear()


def test_paid_coin_checkout_credits_wallet_exactly_once(monkeypatch):
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "test_webhook_signing_secret")
    monkeypatch.setenv("STRIPE_COIN_PACK_25_PRICE_ID", "price_coins_25")
    monkeypatch.setenv("STRIPE_COIN_PACK_75_PRICE_ID", "price_coins_75")
    get_settings.cache_clear()
    session = billing_session()
    user_id = "00000000-0000-0000-0000-000000000003"
    session.add(Profile(id=user_id, email="coins@example.com", tier=SubscriptionTier.FREE))
    session.commit()

    event = {
        "id": "evt_coin_purchase_1",
        "object": "event",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_coin_purchase_1",
                "object": "checkout.session",
                "mode": "payment",
                "payment_status": "paid",
                "customer": "cus_coin_buyer",
                "metadata": {
                    "verifinder_user_id": user_id,
                    "purchase_type": "ask_coins",
                    "coin_pack": "coins_25",
                    "coins": "999",
                },
            }
        },
    }
    payload = json.dumps(event, separators=(",", ":")).encode()
    timestamp = int(time.time())
    digest = hmac.new(
        b"test_webhook_signing_secret", f"{timestamp}.{payload.decode()}".encode(), hashlib.sha256
    ).hexdigest()
    signature = f"t={timestamp},v1={digest}"

    assert process_webhook(session, payload, signature) is True
    assert session.get(CoinWallet, user_id).balance == 25
    assert session.query(CoinTransaction).filter_by(reason="purchase").one().delta == 25
    assert process_webhook(session, payload, signature) is False
    assert session.get(CoinWallet, user_id).balance == 25
    get_settings.cache_clear()


def test_coin_checkout_uses_server_owned_pack_metadata(monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_local")
    monkeypatch.setenv("STRIPE_COIN_PACK_25_PRICE_ID", "price_coins_25")
    monkeypatch.setenv("APP_URL", "https://verifinder.example")
    get_settings.cache_clear()
    captured: dict = {}

    monkeypatch.setattr(
        stripe_billing.stripe.Customer,
        "create",
        lambda **_kwargs: SimpleNamespace(id="cus_coin_checkout"),
    )

    def fake_checkout(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(url="https://checkout.stripe.test/coins")

    monkeypatch.setattr(stripe_billing.stripe.checkout.Session, "create", fake_checkout)
    session = billing_session()
    url = stripe_billing.create_coin_checkout_session(
        session,
        "00000000-0000-0000-0000-000000000004",
        "checkout@example.com",
        "coins_25",
    )

    assert url == "https://checkout.stripe.test/coins"
    assert captured["mode"] == "payment"
    assert captured["payment_method_types"] == ["card"]
    assert captured["line_items"] == [{"price": "price_coins_25", "quantity": 1}]
    assert captured["metadata"]["coins"] == "25"
    assert captured["success_url"] == "https://verifinder.example/ask?coins=success"
    get_settings.cache_clear()
