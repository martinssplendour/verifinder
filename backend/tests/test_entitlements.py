from datetime import datetime, timedelta, timezone

from fastapi import Response
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.billing_models import (
    AppAdmin,
    BillingBase,
    CoinTransaction,
    CoinWallet,
    Profile,
    SubscriptionTier,
    UsageEvent,
)
from app.services.entitlements import (
    _sign,
    _verify,
    check_ask_entitlement,
    check_planner_entitlement,
    check_report_entitlement,
    check_watchlist_entitlement,
    entitlement_snapshot,
    get_or_create_profile,
    record_usage,
    refund_ask_coin,
    reserve_ask,
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


def test_ask_requires_an_account_before_any_quota_is_considered():
    session = entitlements_session()
    result = check_ask_entitlement(session, "anon-2", "Is this school any good?")
    assert result.allowed is False
    assert result.sign_in_required is True
    assert result.code == "ask_sign_in_required"
    assert result.payment_required is False


def test_planner_requires_an_account_before_any_quota_is_considered():
    session = entitlements_session()
    result = check_planner_entitlement(session, "anon-2")
    assert result.allowed is False
    assert result.sign_in_required is True
    assert result.code == "planner_sign_in_required"


def test_ask_entitlement_blocks_over_word_limit():
    session = entitlements_session()
    long_question = " ".join(["word"] * 21)
    result = check_ask_entitlement(session, "member-2", long_question, authenticated=True)
    assert result.allowed is False
    assert "20 words" in (result.message or "")


def test_ask_entitlement_allows_one_free_question_per_day_then_blocks():
    session = entitlements_session()
    first = check_ask_entitlement(session, "member-3", "Is this school any good?", authenticated=True)
    assert first.allowed is True
    record_usage(session, "member-3", "ask", detail="Is this school any good?")

    second = check_ask_entitlement(session, "member-3", "What about this one?", authenticated=True)
    assert second.allowed is False
    assert "free question" in (second.message or "")


def test_ask_entitlement_ignores_daily_limit_after_the_window_elapses():
    session = entitlements_session()
    session.add(Profile(id="member-4", tier=SubscriptionTier.FREE))
    session.add(
        UsageEvent(
            subject_id="member-4",
            feature="ask",
            created_at=datetime.now(timezone.utc) - timedelta(days=2),
        )
    )
    session.commit()
    result = check_ask_entitlement(
        session, "member-4", "Any updates on this company?", authenticated=True
    )
    assert result.allowed is True


def test_ask_entitlement_unlimited_for_paid_tier():
    session = entitlements_session()
    session.add(Profile(id="member-5", tier=SubscriptionTier.PLUS))
    session.commit()
    for _ in range(3):
        result = check_ask_entitlement(
            session, "member-5", " ".join(["word"] * 40), authenticated=True
        )
        assert result.allowed is True
        record_usage(session, "member-5", "ask")


def test_ask_entitlement_enforces_paid_sixty_word_cap():
    session = entitlements_session()
    session.add(Profile(id="paid-1", tier=SubscriptionTier.PLUS))
    session.commit()
    result = check_ask_entitlement(
        session, "paid-1", " ".join(["word"] * 61), authenticated=True
    )
    assert result.allowed is False
    assert "60 words" in (result.message or "")


def test_authenticated_follow_up_atomically_spends_and_refunds_one_coin():
    session = entitlements_session()
    session.add(Profile(id="coin-user", tier=SubscriptionTier.FREE))
    session.add(CoinWallet(subject_id="coin-user", balance=1))
    session.commit()
    record_usage(session, "coin-user", "ask", detail="First free question")

    result = reserve_ask(
        session,
        "coin-user",
        "What about this one?",
        authenticated=True,
    )

    assert result.allowed is True
    assert result.coin_reservation_id
    assert session.get(CoinWallet, "coin-user").balance == 0
    debit = session.query(CoinTransaction).filter_by(reason="ask").one()
    assert debit.delta == -1

    assert refund_ask_coin(session, "coin-user", result.coin_reservation_id) is True
    assert session.get(CoinWallet, "coin-user").balance == 1
    assert refund_ask_coin(session, "coin-user", result.coin_reservation_id) is False


def test_used_free_allowance_asks_a_signed_in_member_to_buy_coins():
    session = entitlements_session()
    record_usage(session, "member-paywall", "ask")
    result = check_ask_entitlement(
        session, "member-paywall", "Can I ask a follow-up?", authenticated=True
    )
    assert result.allowed is False
    assert result.code == "ask_coins_required"
    assert result.payment_required is True
    assert result.sign_in_required is False
    assert "Buy coins" in (result.message or "")


def test_paid_subscription_never_spends_prepaid_coins():
    session = entitlements_session()
    session.add(Profile(id="plus-with-coins", tier=SubscriptionTier.PLUS))
    session.add(CoinWallet(subject_id="plus-with-coins", balance=2))
    session.commit()
    result = reserve_ask(
        session,
        "plus-with-coins",
        "Show me sponsors in Leeds",
        authenticated=True,
    )
    assert result.allowed is True
    assert result.coin_reservation_id is None
    assert session.get(CoinWallet, "plus-with-coins").balance == 2


def test_planner_entitlement_allows_one_free_plan_per_week_then_blocks():
    session = entitlements_session()
    first = check_planner_entitlement(session, "member-6", authenticated=True)
    assert first.allowed is True
    record_usage(session, "member-6", "planner")

    second = check_planner_entitlement(session, "member-6", authenticated=True)
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


def test_admin_grant_bypasses_all_product_entitlement_restrictions():
    session = entitlements_session()
    subject_id = "admin-user"
    email = "okhimhemartins@gmail.com"
    session.add(Profile(id=subject_id, email=email, tier=SubscriptionTier.FREE))
    session.add(AppAdmin(email=email, role="admin", active=True))
    session.commit()
    record_usage(session, subject_id, "ask")
    record_usage(session, subject_id, "planner")

    ask = reserve_ask(
        session,
        subject_id,
        " ".join(["word"] * 100),
        authenticated=True,
        email=email,
    )
    planner = check_planner_entitlement(session, subject_id, authenticated=True, email=email)
    report = check_report_entitlement(session, subject_id, email)
    watchlist = check_watchlist_entitlement(session, subject_id, email)
    snapshot = entitlement_snapshot(session, subject_id, email=email)

    assert ask.allowed is True
    assert ask.tier == SubscriptionTier.PROFESSIONAL
    assert ask.coin_reservation_id is None
    assert planner.allowed is True
    assert report.allowed is True
    assert watchlist.allowed is True
    assert snapshot["tier"] == "professional"
    assert snapshot["ask"]["word_limit"] is None
    assert snapshot["planner"]["allowed"] is True
    assert snapshot["report_download"]["allowed"] is True
    assert snapshot["watchlists"]["allowed"] is True


def test_snapshot_reports_ask_and_planner_closed_for_a_signed_out_visitor():
    session = entitlements_session()
    snapshot = entitlement_snapshot(session, "anon-snapshot")
    assert snapshot["ask"]["allowed"] is False
    assert snapshot["planner"]["allowed"] is False


def test_snapshot_reopens_ask_and_planner_once_signed_in():
    session = entitlements_session()
    session.add(Profile(id="member-snapshot", tier=SubscriptionTier.FREE))
    session.commit()
    snapshot = entitlement_snapshot(session, "member-snapshot")
    assert snapshot["ask"]["allowed"] is True
    assert snapshot["planner"]["allowed"] is True
