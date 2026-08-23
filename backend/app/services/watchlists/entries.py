from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.billing_models import WatchlistAlert, WatchlistEntry
from app.services.dataset_utils import normalise_postcode


def add_watchlist_entry(session: Session, subject_id: str, entity_type: str, entity_id: str, label: str | None = None) -> WatchlistEntry:
    if entity_type == "area":
        entity_id = normalise_postcode(entity_id)
        if not entity_id:
            raise ValueError("A complete Great Britain postcode is required for an area watch.")
    existing = session.scalar(
        select(WatchlistEntry).where(
            WatchlistEntry.subject_id == subject_id,
            WatchlistEntry.entity_type == entity_type,
            WatchlistEntry.entity_id == entity_id,
        )
    )
    if existing:
        return existing
    entry = WatchlistEntry(subject_id=subject_id, entity_type=entity_type, entity_id=entity_id, label=label)
    session.add(entry)
    session.commit()
    return entry


def set_watchlist_notifications(session: Session, subject_id: str, entry_id: int, enabled: bool) -> WatchlistEntry | None:
    entry = session.get(WatchlistEntry, entry_id)
    if entry is None or entry.subject_id != subject_id:
        return None
    entry.notifications_enabled = enabled
    session.commit()
    return entry


def remove_watchlist_entry(session: Session, subject_id: str, entry_id: int) -> bool:
    entry = session.get(WatchlistEntry, entry_id)
    if entry is None or entry.subject_id != subject_id:
        return False
    session.delete(entry)
    session.commit()
    return True


def list_watchlist(session: Session, subject_id: str) -> list[WatchlistEntry]:
    return list(
        session.scalars(
            select(WatchlistEntry).where(WatchlistEntry.subject_id == subject_id).order_by(WatchlistEntry.created_at.desc())
        )
    )


def list_alerts(session: Session, subject_id: str, limit: int = 50) -> list[WatchlistAlert]:
    return list(
        session.scalars(
            select(WatchlistAlert)
            .where(WatchlistAlert.subject_id == subject_id)
            .order_by(WatchlistAlert.created_at.desc())
            .limit(limit)
        )
    )
