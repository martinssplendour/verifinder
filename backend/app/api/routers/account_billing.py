from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.billing_database import get_billing_db
from app.billing_models import Profile, SubscriptionTier
from app.schemas import (
    AccountStatusResponse,
    CheckoutRequest,
    CoinCheckoutRequest,
    RedirectResponse,
    ReportAccessResponse,
)
from app.services.auth import RequestIdentity, identity_dependency, require_authenticated
from app.services.entitlements import (
    check_report_entitlement,
    coin_balance,
    entitlement_snapshot,
    get_or_create_profile,
)
from app.services.stripe_billing import (
    BillingConfigurationError,
    billing_configured,
    coin_billing_configured,
    create_coin_checkout_session,
    create_checkout_session,
    create_portal_session,
    process_webhook,
)


router = APIRouter()


def _entitlement_error(result) -> HTTPException:
    return HTTPException(
        status_code=402 if result.payment_required else 429,
        detail={
            "code": result.code or "upgrade_required",
            "message": result.message or "Upgrade to continue.",
            "upgrade_required": True,
            "payment_required": result.payment_required,
            "sign_in_required": result.sign_in_required,
            "coin_balance": result.coin_balance,
            "reset_at": result.reset_at.isoformat() if result.reset_at else None,
        },
    )


@router.get("/account/me", response_model=AccountStatusResponse)
async def account_status(
    billing_session: Session = Depends(get_billing_db),
    identity: RequestIdentity = Depends(identity_dependency),
):
    if identity.authenticated:
        get_or_create_profile(billing_session, identity.subject_id, identity.email)
    snapshot = entitlement_snapshot(
        billing_session,
        identity.subject_id,
        subject_ids=identity.quota_subject_ids,
        network_hash=identity.network_hash,
    )
    profile = billing_session.get(Profile, identity.subject_id)
    return AccountStatusResponse(
        authenticated=identity.authenticated,
        email=identity.email,
        entitlements=snapshot,
        billing_configured=billing_configured(),
        coin_billing_configured=coin_billing_configured(),
        coin_balance=coin_balance(billing_session, identity.subject_id) if identity.authenticated else 0,
        has_billing_account=bool(profile and profile.stripe_customer_id),
    )


@router.post("/billing/checkout", response_model=RedirectResponse)
async def billing_checkout(
    request: CheckoutRequest,
    billing_session: Session = Depends(get_billing_db),
    identity: RequestIdentity = Depends(identity_dependency),
):
    require_authenticated(identity)
    try:
        url = create_checkout_session(
            billing_session,
            identity.subject_id,
            identity.email,
            SubscriptionTier(request.tier),
            request.cadence,
        )
    except BillingConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    return RedirectResponse(url=url)


@router.post("/billing/coins/checkout", response_model=RedirectResponse)
async def coin_checkout(
    request: CoinCheckoutRequest,
    billing_session: Session = Depends(get_billing_db),
    identity: RequestIdentity = Depends(identity_dependency),
):
    require_authenticated(identity)
    try:
        url = create_coin_checkout_session(
            billing_session,
            identity.subject_id,
            identity.email,
            request.pack,
        )
    except BillingConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    return RedirectResponse(url=url)


@router.post("/billing/portal", response_model=RedirectResponse)
async def billing_portal(
    billing_session: Session = Depends(get_billing_db),
    identity: RequestIdentity = Depends(identity_dependency),
):
    require_authenticated(identity)
    try:
        url = create_portal_session(billing_session, identity.subject_id)
    except BillingConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except LookupError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return RedirectResponse(url=url)


@router.post("/billing/report-access", response_model=ReportAccessResponse)
async def report_access(
    billing_session: Session = Depends(get_billing_db),
    identity: RequestIdentity = Depends(identity_dependency),
):
    result = check_report_entitlement(billing_session, identity.subject_id)
    if not result.allowed:
        raise _entitlement_error(result)
    return ReportAccessResponse(allowed=True)


@router.post("/billing/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
    billing_session: Session = Depends(get_billing_db),
):
    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Missing Stripe-Signature header.")
    payload = await request.body()
    try:
        processed = process_webhook(billing_session, payload, stripe_signature)
    except BillingConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail="Invalid Stripe webhook signature.") from error
    return {"received": True, "processed": processed}
