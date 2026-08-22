from __future__ import annotations

import hashlib
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.billing_models import CompanySnapshot, WatchSnapshot, WatchlistAlert, WatchlistEntry
from app.config import get_settings
from app.models import (
    ChangeEvent,
    DatasetVersion,
    FoodEstablishmentRecord,
    PropertySaleRecord,
    QualificationRecord,
    RunStatus,
    SchoolRecord,
    SponsorRecord,
)
from app.services.food_loader import SOURCE_ID as FOOD_SOURCE_ID
from app.services.gias_loader import SOURCE_ID as GIAS_SOURCE_ID
from app.services.notifications import dispatch_alert_email
from app.services.area_lookup import get_area_check
from app.services.companies_house import CompaniesHouseClient, CompaniesHouseError
from app.services.dataset_utils import normalise_postcode
from app.services.property_loader import SOURCE_ID as PROPERTY_SOURCE_ID
from app.services.qualification_loader import SOURCE_ID as OFQUAL_SOURCE_ID


VERSIONED_DIFF_SPECS: dict[str, tuple[type, str, str, list[str]]] = {
    "school": (SchoolRecord, "urn", GIAS_SOURCE_ID, ["status_name", "type_name", "number_of_pupils"]),
    "food": (FoodEstablishmentRecord, "fhrs_id", FOOD_SOURCE_ID, ["rating_value", "rating_date"]),
    "qualification": (QualificationRecord, "qualification_number", OFQUAL_SOURCE_ID, ["status", "level"]),
}


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


def _latest_and_previous_versions(public_session: Session, source_id: str) -> tuple[DatasetVersion, DatasetVersion] | None:
    versions = list(
        public_session.scalars(
            select(DatasetVersion)
            .where(DatasetVersion.source_id == source_id, DatasetVersion.processing_status == RunStatus.SUCCEEDED)
            .order_by(DatasetVersion.retrieved_at.desc())
            .limit(2)
        )
    )
    if len(versions) < 2:
        return None
    return versions[0], versions[1]


def _diff_fields(old_row: object, new_row: object, fields: list[str]) -> dict[str, tuple[object, object]]:
    changes = {}
    for field in fields:
        old_value = getattr(old_row, field, None)
        new_value = getattr(new_row, field, None)
        if old_value != new_value:
            changes[field] = (old_value, new_value)
    return changes


def _detail_payload(changes: dict[str, tuple[object, object]]) -> dict[str, dict[str, str | None]]:
    return {
        field: {"old": str(old) if old is not None else None, "new": str(new) if new is not None else None}
        for field, (old, new) in changes.items()
    }


def _fingerprint(*parts: object) -> str:
    return hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()


def _alert_seen(session: Session, fingerprint: str) -> bool:
    return session.scalar(select(WatchlistAlert.id).where(WatchlistAlert.fingerprint == fingerprint)) is not None


def _scan_versioned_entity(
    public_session: Session, billing_session: Session, entity_type: str, entries: list[WatchlistEntry]
) -> list[WatchlistAlert]:
    model, key_field, source_id, fields = VERSIONED_DIFF_SPECS[entity_type]
    versions = _latest_and_previous_versions(public_session, source_id)
    if versions is None:
        return []
    current_version, previous_version = versions
    alerts: list[WatchlistAlert] = []
    for entry in entries:
        current_row = public_session.scalar(
            select(model).where(getattr(model, key_field) == entry.entity_id, model.dataset_version_id == current_version.id)
        )
        previous_row = public_session.scalar(
            select(model).where(getattr(model, key_field) == entry.entity_id, model.dataset_version_id == previous_version.id)
        )
        if current_row is None or previous_row is None:
            continue
        changes = _diff_fields(previous_row, current_row, fields)
        if not changes:
            continue
        summary = f"{entry.label or entry.entity_id}: " + "; ".join(
            f"{field} changed from {old!r} to {new!r}" for field, (old, new) in changes.items()
        )
        alert_fingerprint = _fingerprint(entry.id, current_version.id, changes)
        if _alert_seen(billing_session, alert_fingerprint):
            continue
        alert = WatchlistAlert(
            watchlist_entry_id=entry.id,
            subject_id=entry.subject_id,
            entity_type=entity_type,
            entity_id=entry.entity_id,
            fingerprint=alert_fingerprint,
            summary=summary,
            detail=_detail_payload(changes),
        )
        billing_session.add(alert)
        alerts.append(alert)
    if alerts:
        billing_session.commit()
    return alerts


def _scan_property_entities(public_session: Session, billing_session: Session, entries: list[WatchlistEntry]) -> list[WatchlistAlert]:
    versions = _latest_and_previous_versions(public_session, PROPERTY_SOURCE_ID)
    if versions is None:
        return []
    current_version, previous_version = versions
    alerts: list[WatchlistAlert] = []
    for entry in entries:
        current_ids = set(
            public_session.scalars(
                select(PropertySaleRecord.transaction_id).where(
                    PropertySaleRecord.property_key == entry.entity_id,
                    PropertySaleRecord.dataset_version_id == current_version.id,
                )
            )
        )
        previous_ids = set(
            public_session.scalars(
                select(PropertySaleRecord.transaction_id).where(
                    PropertySaleRecord.property_key == entry.entity_id,
                    PropertySaleRecord.dataset_version_id == previous_version.id,
                )
            )
        )
        new_ids = current_ids - previous_ids
        if not new_ids:
            continue
        alert_fingerprint = _fingerprint(entry.id, current_version.id, sorted(new_ids))
        if _alert_seen(billing_session, alert_fingerprint):
            continue
        alert = WatchlistAlert(
            watchlist_entry_id=entry.id,
            subject_id=entry.subject_id,
            entity_type="property",
            entity_id=entry.entity_id,
            fingerprint=alert_fingerprint,
            summary=f"{entry.label or entry.entity_id}: {len(new_ids)} new recorded sale(s).",
            detail={"new_transaction_ids": sorted(new_ids)},
        )
        billing_session.add(alert)
        alerts.append(alert)
    if alerts:
        billing_session.commit()
    return alerts


def _scan_sponsor_entities(public_session: Session, billing_session: Session, entries: list[WatchlistEntry]) -> list[WatchlistAlert]:
    alerts: list[WatchlistAlert] = []
    for entry in entries:
        record = public_session.get(SponsorRecord, entry.entity_id)
        if record is None:
            continue
        events = list(
            public_session.scalars(
                select(ChangeEvent)
                .where(ChangeEvent.source_record_key == record.source_record_key)
                .order_by(ChangeEvent.detected_at.desc())
                .limit(5)
            )
        )
        already_alerted = {
            row.detail.get("change_event_id")
            for row in billing_session.scalars(select(WatchlistAlert).where(WatchlistAlert.watchlist_entry_id == entry.id))
            if row.detail
        }
        for event in events:
            if event.id in already_alerted:
                continue
            alert_fingerprint = _fingerprint(entry.id, event.id)
            if _alert_seen(billing_session, alert_fingerprint):
                continue
            alert = WatchlistAlert(
                watchlist_entry_id=entry.id,
                subject_id=entry.subject_id,
                entity_type="sponsor",
                entity_id=entry.entity_id,
                fingerprint=alert_fingerprint,
                summary=f"{entry.label or record.organisation_name}: {event.change_type.replace('_', ' ')}.",
                detail={"change_event_id": event.id, "change_type": event.change_type},
            )
            billing_session.add(alert)
            alerts.append(alert)
    if alerts:
        billing_session.commit()
    return alerts


def snapshot_company(
    billing_session: Session,
    company_number: str,
    *,
    company_status: str | None,
    sic_codes: list[str] | None,
    accounts_next_due: str | None,
    officer_count: int | None,
) -> None:
    sic_hash = hashlib.sha256(",".join(sorted(sic_codes or [])).encode("utf-8")).hexdigest() if sic_codes else None
    billing_session.add(
        CompanySnapshot(
            company_number=company_number,
            company_status=company_status,
            sic_codes_hash=sic_hash,
            accounts_next_due=accounts_next_due,
            officer_count=officer_count,
        )
    )
    billing_session.commit()


def _scan_company_entities(billing_session: Session, entries: list[WatchlistEntry]) -> list[WatchlistAlert]:
    alerts: list[WatchlistAlert] = []
    for entry in entries:
        snapshots = list(
            billing_session.scalars(
                select(CompanySnapshot)
                .where(CompanySnapshot.company_number == entry.entity_id)
                .order_by(CompanySnapshot.checked_at.desc())
                .limit(2)
            )
        )
        if len(snapshots) < 2:
            continue
        current, previous = snapshots
        changes = _diff_fields(previous, current, ["company_status", "sic_codes_hash", "accounts_next_due"])
        if not changes:
            continue
        alert_fingerprint = _fingerprint(entry.id, current.id, changes)
        if _alert_seen(billing_session, alert_fingerprint):
            continue
        alert = WatchlistAlert(
            watchlist_entry_id=entry.id,
            subject_id=entry.subject_id,
            entity_type="company",
            entity_id=entry.entity_id,
            fingerprint=alert_fingerprint,
            summary=f"{entry.label or entry.entity_id}: " + "; ".join(f"{field} changed" for field in changes),
            detail=_detail_payload(changes),
        )
        billing_session.add(alert)
        alerts.append(alert)
    if alerts:
        billing_session.commit()
    return alerts


def scan_for_changes(public_session: Session, billing_session: Session) -> list[WatchlistAlert]:
    entries = list(billing_session.scalars(select(WatchlistEntry)))
    by_type: dict[str, list[WatchlistEntry]] = {}
    for entry in entries:
        by_type.setdefault(entry.entity_type, []).append(entry)

    alerts: list[WatchlistAlert] = []
    for entity_type in VERSIONED_DIFF_SPECS:
        if entity_type in by_type:
            alerts.extend(_scan_versioned_entity(public_session, billing_session, entity_type, by_type[entity_type]))
    if "property" in by_type:
        alerts.extend(_scan_property_entities(public_session, billing_session, by_type["property"]))
    if "sponsor" in by_type:
        alerts.extend(_scan_sponsor_entities(public_session, billing_session, by_type["sponsor"]))
    if "company" in by_type:
        alerts.extend(_scan_company_entities(billing_session, by_type["company"]))
    for alert in alerts:
        dispatch_alert_email(billing_session, alert)
    return alerts


def _stable_payload(value: dict) -> tuple[str, dict]:
    serialised = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(serialised.encode("utf-8")).hexdigest(), value


def _record_live_snapshot(
    billing_session: Session,
    entry: WatchlistEntry,
    payload: dict,
) -> WatchlistAlert | None:
    fingerprint, payload = _stable_payload(payload)
    previous = billing_session.scalar(
        select(WatchSnapshot)
        .where(WatchSnapshot.watchlist_entry_id == entry.id)
        .order_by(WatchSnapshot.checked_at.desc())
        .limit(1)
    )
    if previous and previous.fingerprint == fingerprint:
        return None
    billing_session.add(WatchSnapshot(watchlist_entry_id=entry.id, fingerprint=fingerprint, detail=payload))
    alert = None
    if previous:
        changed = sorted(key for key in set(previous.detail) | set(payload) if previous.detail.get(key) != payload.get(key))
        alert_fingerprint = _fingerprint(entry.id, fingerprint)
        if _alert_seen(billing_session, alert_fingerprint):
            billing_session.commit()
            return None
        alert = WatchlistAlert(
            watchlist_entry_id=entry.id,
            subject_id=entry.subject_id,
            entity_type=entry.entity_type,
            entity_id=entry.entity_id,
            fingerprint=alert_fingerprint,
            summary=f"{entry.label or entry.entity_id}: {', '.join(changed) or 'official record'} changed.",
            detail={key: {"old": previous.detail.get(key), "new": payload.get(key)} for key in changed},
        )
        billing_session.add(alert)
    billing_session.commit()
    if alert:
        dispatch_alert_email(billing_session, alert)
    return alert


async def scan_live_watchlists(public_session: Session, billing_session: Session) -> list[WatchlistAlert]:
    """Capture current Companies House and postcode-area states and alert only on a changed fingerprint."""
    entries = list(
        billing_session.scalars(
            select(WatchlistEntry).where(WatchlistEntry.entity_type.in_(["company", "area"]))
        )
    )
    settings = get_settings()
    company_client = CompaniesHouseClient(settings.companies_house_api_key) if settings.companies_house_api_key else None
    alerts: list[WatchlistAlert] = []
    for entry in entries:
        payload = None
        if entry.entity_type == "company" and company_client:
            try:
                profile = await company_client.profile(entry.entity_id)
                payload = {
                    "company_status": profile.company_status,
                    "registered_office": profile.registered_office,
                    "accounts_next_due": str(profile.accounts_next_due) if profile.accounts_next_due else None,
                    "sic_codes": sorted(profile.sic_codes),
                }
            except (CompaniesHouseError, KeyError):
                continue
        elif entry.entity_type == "area":
            area = await get_area_check(public_session, entry.entity_id)
            if area:
                payload = {
                    "crime_latest_month": area.crime.latest_month,
                    "crime_latest_total": area.crime.latest_total,
                    "planning_total": area.planning.total,
                    "flood_total": area.flood.total,
                    "flood_severities": sorted(warning.severity for warning in area.flood.warnings),
                }
        if payload is not None:
            alert = _record_live_snapshot(billing_session, entry, payload)
            if alert:
                alerts.append(alert)
    return alerts
