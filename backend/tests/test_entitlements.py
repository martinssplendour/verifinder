from datetime import datetime, timedelta, timezone

from fastapi import Response
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.billing_models import BillingBase, Profile, SubscriptionTier, UsageEvent
from app.services.entitlements import (
    _sign,
    _verify,
    check_ask_entitlement,
    check_planner_entitlement,
    check_report_entitlement,
    get_or_create_profile,
    record_usage,
    resolve_subject_id,
)


def entitlements_session() -> Session:
    engine = create_engine("sqlite://")
    BillingBase.metadata.create_all(engine)
    return Session(engine)


def test_sign_and_verify_round_trip():
    token = _sign("anon-abc123")
    assert _verify(token) == "anon-abc123"


def test_verify_rejects_tampered_signature():
    token = _sign("anon-abc123")
    tampered = token[:-1] + ("0" if token[-1] != "0" else "1")
    assert _verify(tampered) is None


def test_verify_rejects_malformed_token():
    assert _verify("no-dot-here") is None


def test_resolve_subject_id_issues_new_cookie_when_absent():
    response = Response()
    subject_id = resolve_subject_id(response, vf_subject=None)
    assert subject_id.startswith("anon-")
    assert "vf_subject" in response.headers.get("set-cookie", "")


def test_resolve_subject_id_reuses_valid_cookie_without_resetting_it():
    existing = _sign("anon-existing")
    response = Response()
    subject_id = resolve_subject_id(response, vf_subject=existing)
    assert subject_id == "anon-existing"
    assert "set-cookie" not in {k.lower() for k in response.headers.keys()}


def test_resolve_subject_id_issues_fresh_subject_for_tampered_cookie():
    response = Response()
    subject_id = resolve_subject_id(response, vf_subject="garbage.notasignature")
    assert subject_id.startswith("anon-")
    assert subject_id != "garbage"


def test_get_or_create_profile_defaults_to_free_tier():
    session = entitlements_session()
    profile = get_or_create_profile(session, "anon-1")
    assert profile.tier == SubscriptionTier.FREE
    again = get_or_create_profile(session, "anon-1")
    assert again.id == profile.id


def test_ask_entitlement_blocks_over_word_limit():
    session = entitlements_session()
    long_question = " ".join(["word"] * 21)
    result = check_ask_entitlement(session, "anon-2", long_question)
    assert result.allowed is False
    assert "20 words" in (result.message or "")


def test_ask_entitlement_allows_one_free_question_per_day_then_blocks():
    session = entitlements_session()
    first = check_ask_entitlement(session, "anon-3", "Is this school any good?")
    assert first.allowed is True
    record_usage(session, "anon-3", "ask", detail="Is this school any good?")

    second = check_ask_entitlement(session, "anon-3", "What about this one?")
    assert second.allowed is False
    assert "free question" in (second.message or "")


def test_ask_entitlement_ignores_daily_limit_after_the_window_elapses():
    session = entitlements_session()
    session.add(Profile(id="anon-4", tier=SubscriptionTier.FREE))
    session.add(
        UsageEvent(
            subject_id="anon-4",
            feature="ask",
            created_at=datetime.now(timezone.utc) - timedelta(days=2),
        )
    )
    session.commit()
    result = check_ask_entitlement(session, "anon-4", "Any updates on this company?")
    assert result.allowed is True


def test_ask_entitlement_unlimited_for_paid_tier():
    session = entitlements_session()
    session.add(Profile(id="anon-5", tier=SubscriptionTier.PLUS))
    session.commit()
    for _ in range(3):
        result = check_ask_entitlement(session, "anon-5", " ".join(["word"] * 40))
        assert result.allowed is True
        record_usage(session, "anon-5", "ask")


def test_ask_entitlement_enforces_paid_sixty_word_cap():
    session = entitlements_session()
    session.add(Profile(id="paid-1", tier=SubscriptionTier.PLUS))
    session.commit()
    result = check_ask_entitlement(session, "paid-1", " ".join(["word"] * 61))
    assert result.allowed is False
    assert "60 words" in (result.message or "")


def test_planner_entitlement_allows_one_free_plan_per_week_then_blocks():
    session = entitlements_session()
    first = check_planner_entitlement(session, "anon-6")
    assert first.allowed is True
    record_usage(session, "anon-6", "planner")

    second = check_planner_entitlement(session, "anon-6")
    assert second.allowed is False
    assert "free plan" in (second.message or "")


def test_report_entitlement_always_blocked_on_free_tier():
    session = entitlements_session()
    result = check_report_entitlement(session, "anon-7")
    assert result.allowed is False


def test_report_entitlement_allowed_on_professional_tier():
    session = entitlements_session()
    session.add(Profile(id="anon-8", tier=SubscriptionTier.PROFESSIONAL))
    session.commit()
    result = check_report_entitlement(session, "anon-8")
    assert result.allowed is True
