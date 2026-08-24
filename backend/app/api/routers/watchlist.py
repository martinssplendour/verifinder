from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.routers.account_billing import _entitlement_error
from app.billing_database import get_billing_db
from app.schemas import (
    WatchlistAlertView,
    WatchlistEntryCreate,
    WatchlistEntryUpdate,
    WatchlistEntryView,
)
from app.services.auth import RequestIdentity, identity_dependency, require_authenticated
from app.services.entitlements import check_watchlist_entitlement
from app.services.watchlists import (
    add_watchlist_entry,
    list_alerts,
    list_watchlist,
    remove_watchlist_entry,
    set_watchlist_notifications,
)


router = APIRouter()


def _watchlist_entry_view(entry) -> WatchlistEntryView:
    return WatchlistEntryView(
        id=entry.id,
        entity_type=entry.entity_type,
        entity_id=entry.entity_id,
        label=entry.label,
        notifications_enabled=entry.notifications_enabled,
        created_at=entry.created_at,
    )


def _watchlist_alert_view(alert) -> WatchlistAlertView:
    return WatchlistAlertView(
        id=alert.id,
        entity_type=alert.entity_type,
        entity_id=alert.entity_id,
        summary=alert.summary,
        detail=alert.detail,
        email_status=alert.email_status,
        created_at=alert.created_at,
    )


@router.post("/watchlist", response_model=WatchlistEntryView)
async def add_to_watchlist(
    request: WatchlistEntryCreate,
    billing_session: Session = Depends(get_billing_db),
    identity: RequestIdentity = Depends(identity_dependency),
):
    require_authenticated(identity)
    entitlement = check_watchlist_entitlement(billing_session, identity.subject_id, identity.email)
    if not entitlement.allowed:
        raise _entitlement_error(entitlement)
    try:
        entry = add_watchlist_entry(
            billing_session, identity.subject_id, request.entity_type, request.entity_id, request.label
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return _watchlist_entry_view(entry)


@router.patch("/watchlist/{entry_id}", response_model=WatchlistEntryView)
async def update_watchlist_entry(
    entry_id: int,
    request: WatchlistEntryUpdate,
    billing_session: Session = Depends(get_billing_db),
    identity: RequestIdentity = Depends(identity_dependency),
):
    require_authenticated(identity)
    entry = set_watchlist_notifications(
        billing_session, identity.subject_id, entry_id, request.notifications_enabled
    )
    if entry is None:
        raise HTTPException(status_code=404, detail="Watchlist entry not found.")
    return _watchlist_entry_view(entry)


@router.delete("/watchlist/{entry_id}")
async def remove_from_watchlist(
    entry_id: int,
    billing_session: Session = Depends(get_billing_db),
    identity: RequestIdentity = Depends(identity_dependency),
):
    require_authenticated(identity)
    if not remove_watchlist_entry(billing_session, identity.subject_id, entry_id):
        raise HTTPException(status_code=404, detail="Watchlist entry not found.")
    return {"status": "removed"}


@router.get("/watchlist", response_model=list[WatchlistEntryView])
async def get_watchlist(
    billing_session: Session = Depends(get_billing_db),
    identity: RequestIdentity = Depends(identity_dependency),
):
    require_authenticated(identity)
    return [_watchlist_entry_view(entry) for entry in list_watchlist(billing_session, identity.subject_id)]


@router.get("/watchlist/alerts", response_model=list[WatchlistAlertView])
async def get_watchlist_alerts(
    limit: int = Query(default=50, ge=1, le=200),
    billing_session: Session = Depends(get_billing_db),
    identity: RequestIdentity = Depends(identity_dependency),
):
    require_authenticated(identity)
    return [_watchlist_alert_view(alert) for alert in list_alerts(billing_session, identity.subject_id, limit)]
