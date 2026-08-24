"""Browsing a register: everything by default, narrowed when a place is chosen."""

from datetime import date, datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from fastapi.testclient import TestClient

from app.database import Base, get_read_db
from app.main import app
from app.models import (
    DataSource,
    DatasetVersion,
    PropertySaleRecord,
    RunStatus,
    SourceHealth,
    SponsorRecord,
)
from app.services.browse import BROWSABLE, COUNTRIES


RETRIEVED = datetime(2026, 8, 24, tzinfo=timezone.utc)


def _source(source_id: str, organisation: str) -> DataSource:
    return DataSource(
        id=source_id,
        organisation=organisation,
        name=f"{organisation} register",
        source_type="CSV",
        official_url="https://example.test/source",
        country="GB",
        health=SourceHealth.HEALTHY,
        last_successful_retrieval=RETRIEVED,
    )


def _version(source_id: str, version_id: str, character: str) -> DatasetVersion:
    return DatasetVersion(
        id=version_id,
        source_id=source_id,
        version_identifier="2026-08-24",
        retrieved_at=RETRIEVED,
        published_at=RETRIEVED,
        file_hash=character * 64,
        record_count=1,
        storage_location="source.csv",
        processing_status=RunStatus.SUCCEEDED,
    )


def _sponsor(key: str, name: str, town: str, active: bool = True) -> SponsorRecord:
    return SponsorRecord(
        dataset_version_id="sponsor-version",
        source_record_key=key * 64,
        organisation_name=name,
        normalised_name=name.lower(),
        town_city=town,
        county=None,
        sponsor_rating="Worker (A rating)",
        routes=["Skilled Worker"],
        active=active,
        raw_record=[],
    )


def browse_client(session: Session) -> TestClient:
    """A client bound to one in-memory register, so routes run as they really do."""
    app.dependency_overrides[get_read_db] = lambda: session
    client = TestClient(app)
    client.__exit__ = lambda *_: app.dependency_overrides.clear()
    return client


def browse_session() -> Session:
    # The test client serves requests on another thread, and a plain in-memory
    # SQLite gives every connection its own empty database. StaticPool keeps all
    # of them on the one connection so the seeded rows are actually visible.
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = Session(engine)
    session.add_all(
        [
            _source("home-office-worker-sponsors", "UK Visas and Immigration"),
            _version("home-office-worker-sponsors", "sponsor-version", "a"),
            _sponsor("a", "Alpha Systems Ltd", "Manchester"),
            _sponsor("b", "Beta Digital Ltd", "London"),
            _sponsor("c", "Gamma Data Ltd", "Manchester"),
            _sponsor("d", "Delta Retired Ltd", "Manchester", active=False),
        ]
    )
    session.commit()
    return session


def test_catalogue_lists_every_register_and_the_countries_covered():
    client = browse_client(browse_session())
    catalogue = client.get("/api/browse").json()
    assert [country["code"] for country in catalogue["countries"]] == ["GB"]
    assert {dataset["id"] for dataset in catalogue["datasets"]} == set(BROWSABLE)
    sponsors = next(item for item in catalogue["datasets"] if item["id"] == "sponsors")
    assert sponsors["imported"] is True
    assert sponsors["place_label"] == "Town or city"
    # A register with no address holds no place to filter on.
    qualifications = next(item for item in catalogue["datasets"] if item["id"] == "qualifications")
    assert qualifications["place_label"] is None
    assert qualifications["imported"] is False
    assert "not been imported" in (qualifications["message"] or "")


def test_browsing_without_a_filter_returns_the_whole_register():
    client = browse_client(browse_session())
    payload = client.get("/api/browse/sponsors").json()
    assert payload["total"] == 3
    assert [record["title"] for record in payload["records"]] == [
        "Alpha Systems Ltd",
        "Beta Digital Ltd",
        "Gamma Data Ltd",
    ]
    assert payload["source"]["organisation"] == "UK Visas and Immigration"


def test_a_place_filter_narrows_the_register_to_that_vicinity():
    client = browse_client(browse_session())
    payload = client.get("/api/browse/sponsors", params={"place": "Manchester"}).json()
    assert payload["total"] == 2
    assert [record["title"] for record in payload["records"]] == ["Alpha Systems Ltd", "Gamma Data Ltd"]
    assert payload["place"] == "Manchester"


def test_the_place_filter_ignores_casing():
    client = browse_client(browse_session())
    payload = client.get("/api/browse/sponsors", params={"place": "manchester"}).json()
    assert payload["total"] == 2


def test_withdrawn_records_are_left_out_of_the_listing():
    client = browse_client(browse_session())
    payload = client.get("/api/browse/sponsors").json()
    assert "Delta Retired Ltd" not in [record["title"] for record in payload["records"]]


def test_places_come_from_the_register_itself():
    client = browse_client(browse_session())
    assert client.get("/api/browse/sponsors/places").json() == ["London", "Manchester"]


def test_a_register_without_a_place_offers_no_filter_options():
    client = browse_client(browse_session())
    assert client.get("/api/browse/qualifications/places").json() == []


def test_pages_do_not_overlap():
    client = browse_client(browse_session())
    first = client.get("/api/browse/sponsors", params={"page": 1, "page_size": 2}).json()
    second = client.get("/api/browse/sponsors", params={"page": 2, "page_size": 2}).json()
    assert [record["title"] for record in first["records"]] == ["Alpha Systems Ltd", "Beta Digital Ltd"]
    assert [record["title"] for record in second["records"]] == ["Gamma Data Ltd"]
    assert first["total"] == second["total"] == 3


def test_an_unimported_register_reports_itself_rather_than_failing():
    client = browse_client(browse_session())
    payload = client.get("/api/browse/food").json()
    assert payload["records"] == []
    assert payload["total"] == 0
    assert "not been imported" in (payload["message"] or "")


def test_an_unknown_register_is_a_404():
    client = browse_client(browse_session())
    assert client.get("/api/browse/nonsense").status_code == 404


def test_a_country_we_hold_nothing_for_is_a_404():
    client = browse_client(browse_session())
    assert client.get("/api/browse/sponsors", params={"country": "FR"}).status_code == 404
    assert [country.code for country in COUNTRIES] == ["GB"]


def test_an_oversized_page_is_rejected_by_the_route():
    client = browse_client(browse_session())
    assert client.get("/api/browse/sponsors", params={"page_size": 5000}).status_code == 422


def test_repeated_sales_of_one_property_are_a_single_entry():
    session = browse_session()
    session.add_all(
        [
            _source("hm-land-registry-price-paid", "HM Land Registry"),
            _version("hm-land-registry-price-paid", "property-version", "b"),
        ]
    )
    session.add_all(
        [
            PropertySaleRecord(
                dataset_version_id="property-version",
                transaction_id=f"tx-{index}",
                price=price,
                transfer_date=sold,
                postcode="M1 1AA",
                normalised_postcode="M11AA",
                property_type="F",
                new_build=False,
                tenure="L",
                paon="1",
                street="EXAMPLE STREET",
                town_city="Manchester",
                full_address="1, EXAMPLE STREET, MANCHESTER, M1 1AA",
                normalised_address="1 example street manchester m1 1aa",
                property_key="property-key",
                ppd_category="A",
                record_status="A",
            )
            for index, (price, sold) in enumerate(((250000, date(2025, 3, 1)), (275000, date(2026, 2, 1))), start=1)
        ]
    )
    session.commit()

    payload = browse_client(session).get("/api/browse/property", params={"place": "Manchester"}).json()
    assert payload["total"] == 1
    assert len(payload["records"]) == 1
    assert payload["records"][0]["href"] == "/property/property-key"
