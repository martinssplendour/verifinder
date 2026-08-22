from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.billing_models import BillingBase
from app.database import Base
from app.models import DataSource, DatasetVersion, PropertySaleRecord, RunStatus, SchoolRecord, SourceHealth
from app.services.gias_loader import SOURCE_ID as GIAS_SOURCE_ID
from app.services.property_loader import SOURCE_ID as PROPERTY_SOURCE_ID
from app.services.watchlists import (
    _scan_company_entities,
    add_watchlist_entry,
    list_alerts,
    list_watchlist,
    remove_watchlist_entry,
    scan_for_changes,
    snapshot_company,
)


def public_session() -> Session:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    return Session(engine)


def billing_session() -> Session:
    engine = create_engine("sqlite://")
    BillingBase.metadata.create_all(engine)
    return Session(engine)


def _source(source_id: str, organisation: str) -> DataSource:
    return DataSource(
        id=source_id, organisation=organisation, name=organisation, source_type="CSV",
        official_url="https://example.test", country="GB", health=SourceHealth.HEALTHY,
    )


def _version(source_id: str, version_id: str, retrieved: datetime, hash_character: str) -> DatasetVersion:
    return DatasetVersion(
        id=version_id, source_id=source_id, version_identifier=version_id, retrieved_at=retrieved,
        file_hash=hash_character * 64, record_count=1, storage_location="fixture",
        processing_status=RunStatus.SUCCEEDED,
    )


def test_add_watchlist_entry_is_idempotent():
    billing = billing_session()
    first = add_watchlist_entry(billing, "user-1", "company", "08804411", label="Revolut Ltd")
    second = add_watchlist_entry(billing, "user-1", "company", "08804411", label="Revolut Ltd (again)")
    assert first.id == second.id
    assert len(list_watchlist(billing, "user-1")) == 1


def test_area_watchlist_normalises_postcode():
    billing = billing_session()
    entry = add_watchlist_entry(billing, "user-1", "area", "m1 1ae", label="Manchester city centre")
    assert entry.entity_id == "M11AE"


def test_remove_watchlist_entry_only_removes_own_entry():
    billing = billing_session()
    entry = add_watchlist_entry(billing, "user-1", "company", "08804411")
    assert remove_watchlist_entry(billing, "user-2", entry.id) is False
    assert remove_watchlist_entry(billing, "user-1", entry.id) is True
    assert list_watchlist(billing, "user-1") == []


def test_scan_for_changes_detects_school_status_change():
    public = public_session()
    billing = billing_session()

    older = datetime(2026, 8, 1, tzinfo=timezone.utc)
    newer = datetime(2026, 8, 22, tzinfo=timezone.utc)
    public.add(_source(GIAS_SOURCE_ID, "Department for Education"))
    public.add(_version(GIAS_SOURCE_ID, "v-old", older, "1"))
    public.add(_version(GIAS_SOURCE_ID, "v-new", newer, "2"))
    public.add(SchoolRecord(
        dataset_version_id="v-old", urn="100000", establishment_name="Gospel Oak Primary School",
        normalised_name="gospel oak primary school", status_name="Open", number_of_pupils=400, raw_record={},
    ))
    public.add(SchoolRecord(
        dataset_version_id="v-new", urn="100000", establishment_name="Gospel Oak Primary School",
        normalised_name="gospel oak primary school", status_name="Closed", number_of_pupils=400, raw_record={},
    ))
    public.commit()

    add_watchlist_entry(billing, "user-1", "school", "100000", label="Gospel Oak Primary School")
    alerts = scan_for_changes(public, billing)

    assert len(alerts) == 1
    assert alerts[0].entity_type == "school"
    assert "status_name" in alerts[0].summary or "Open" in alerts[0].summary
    assert list_alerts(billing, "user-1")[0].detail["status_name"] == {"old": "Open", "new": "Closed"}


def test_scan_for_changes_detects_new_property_sale():
    public = public_session()
    billing = billing_session()

    older = datetime(2026, 7, 1, tzinfo=timezone.utc)
    newer = datetime(2026, 8, 22, tzinfo=timezone.utc)
    public.add(_source(PROPERTY_SOURCE_ID, "HM Land Registry"))
    public.add(_version(PROPERTY_SOURCE_ID, "v-old", older, "3"))
    public.add(_version(PROPERTY_SOURCE_ID, "v-new", newer, "4"))
    public.add(PropertySaleRecord(
        dataset_version_id="v-old", transaction_id="tx-1", price=500000, transfer_date=older.date(),
        property_key="prop-key-1", full_address="1 Example Street", normalised_address="1 example street",
    ))
    public.add(PropertySaleRecord(
        dataset_version_id="v-new", transaction_id="tx-1", price=500000, transfer_date=older.date(),
        property_key="prop-key-1", full_address="1 Example Street", normalised_address="1 example street",
    ))
    public.add(PropertySaleRecord(
        dataset_version_id="v-new", transaction_id="tx-2", price=550000, transfer_date=newer.date(),
        property_key="prop-key-1", full_address="1 Example Street", normalised_address="1 example street",
    ))
    public.commit()

    add_watchlist_entry(billing, "user-1", "property", "prop-key-1")
    alerts = scan_for_changes(public, billing)

    assert len(alerts) == 1
    assert alerts[0].detail["new_transaction_ids"] == ["tx-2"]


def test_scan_for_changes_ignores_unwatched_entities():
    public = public_session()
    billing = billing_session()
    alerts = scan_for_changes(public, billing)
    assert alerts == []


def test_company_snapshot_diff_detects_status_change():
    billing = billing_session()
    entry = add_watchlist_entry(billing, "user-1", "company", "08804411", label="Revolut Ltd")

    snapshot_company(billing, "08804411", company_status="active", sic_codes=["64110"], accounts_next_due="2026-01-01", officer_count=5)
    snapshot_company(billing, "08804411", company_status="dissolved", sic_codes=["64110"], accounts_next_due="2026-01-01", officer_count=5)

    alerts = _scan_company_entities(billing, [entry])
    assert len(alerts) == 1
    assert alerts[0].detail["company_status"] == {"old": "active", "new": "dissolved"}


def test_company_snapshot_no_alert_without_change():
    billing = billing_session()
    entry = add_watchlist_entry(billing, "user-1", "company", "08804411")
    snapshot_company(billing, "08804411", company_status="active", sic_codes=None, accounts_next_due=None, officer_count=None)
    snapshot_company(billing, "08804411", company_status="active", sic_codes=None, accounts_next_due=None, officer_count=None)
    assert _scan_company_entities(billing, [entry]) == []
