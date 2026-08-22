import asyncio
import hashlib
import hmac
import json
import time

from fastapi import Response
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.billing_models import BillingBase, Profile, Subscription, SubscriptionTier
from app.config import get_settings
from app.services import auth
from app.services.entitlements import _sign
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
