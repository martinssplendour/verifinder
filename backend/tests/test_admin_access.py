import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.billing_models import AppAdmin, BillingBase
from app.services.admin_access import active_admin_grant, require_app_admin
from app.services.auth import RequestIdentity


def admin_session() -> Session:
    engine = create_engine("sqlite://")
    BillingBase.metadata.create_all(engine)
    return Session(engine)


def identity(email: str | None, *, authenticated: bool = True) -> RequestIdentity:
    user_id = "admin-user" if authenticated else None
    subject_id = user_id or "anon-user"
    return RequestIdentity(
        subject_id=subject_id,
        anonymous_subject_id="anon-user",
        network_hash=None,
        user_id=user_id,
        email=email,
    )


def test_active_admin_grant_is_case_insensitive():
    session = admin_session()
    session.add(AppAdmin(email="okhimhemartins@gmail.com", role="admin", active=True))
    session.commit()

    grant = active_admin_grant(session, "OkhimheMartins@GMAIL.COM")

    assert grant is not None
    assert grant.role == "admin"


@pytest.mark.parametrize(
    ("grant", "email"),
    [
        (None, "unknown@example.com"),
        (AppAdmin(email="inactive@example.com", role="admin", active=False), "inactive@example.com"),
        (AppAdmin(email="viewer@example.com", role="viewer", active=True), "viewer@example.com"),
    ],
)
def test_non_admin_grants_are_rejected(grant, email):
    session = admin_session()
    if grant is not None:
        session.add(grant)
        session.commit()

    with pytest.raises(HTTPException) as error:
        require_app_admin(session, identity(email))

    assert error.value.status_code == 403


def test_anonymous_admin_request_requires_sign_in():
    session = admin_session()

    with pytest.raises(HTTPException) as error:
        require_app_admin(session, identity(None, authenticated=False))

    assert error.value.status_code == 401
