from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.billing_models import AppAdmin
from app.services.auth import RequestIdentity


ADMIN_ROLE = "admin"


def normalise_admin_email(email: str) -> str:
    return email.strip().casefold()


def active_admin_grant(session: Session, email: str | None) -> AppAdmin | None:
    if not email:
        return None
    grant = session.get(AppAdmin, normalise_admin_email(email))
    if grant is None or not grant.active or grant.role != ADMIN_ROLE:
        return None
    return grant


def require_app_admin(session: Session, identity: RequestIdentity) -> AppAdmin:
    if not identity.authenticated:
        raise HTTPException(
            status_code=401,
            detail={
                "code": "admin_sign_in_required",
                "message": "Sign in with a VeriFinder administrator account.",
                "sign_in_required": True,
            },
        )
    grant = active_admin_grant(session, identity.email)
    if grant is None:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "admin_access_denied",
                "message": "This account does not have VeriFinder administrator access.",
            },
        )
    return grant
