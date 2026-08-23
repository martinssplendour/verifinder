from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database import Base
from app.models import DataSource, DatasetVersion, RunStatus, SourceHealth, SponsorRecord
from app.services.sponsor_lookup import get_sponsor_record, search_sponsor_records, suggest_sponsor_records


def sponsor_session() -> Session:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = Session(engine)
    retrieved = datetime(2026, 8, 21, tzinfo=timezone.utc)
    source = DataSource(
        id="home-office-worker-sponsors",
        organisation="UK Visas and Immigration",
        name="Register of licensed sponsors: workers",
        source_type="CSV",
        official_url="https://www.gov.uk/government/publications/register-of-licensed-sponsors-workers",
        data_url=None,
        country="GB",
        refresh_frequency="Checked daily",
        health=SourceHealth.HEALTHY,
        last_successful_retrieval=retrieved,
    )
    version = DatasetVersion(
        id="version-1",
        source_id=source.id,
        version_identifier="2026-08-20-example",
        retrieved_at=retrieved,
        published_at=retrieved,
        file_hash="a" * 64,
        record_count=1,
        storage_location="raw.csv",
        processing_status=RunStatus.SUCCEEDED,
    )
    sponsor = SponsorRecord(
        dataset_version_id=version.id,
        source_record_key="b" * 64,
        organisation_name="Northstar Labs Ltd",
        normalised_name="northstar labs limited",
        town_city="London",
        county=None,
        sponsor_rating="Worker (A rating)",
        routes=["Skilled Worker", "Scale-up"],
        active=True,
        raw_record=[],
    )
    similar_sponsor = SponsorRecord(
        dataset_version_id=version.id,
        source_record_key="c" * 64,
        organisation_name="Northstar Arts CIO",
        normalised_name="northstar arts cio",
        town_city="Luton",
        county=None,
        sponsor_rating="Worker (A rating)",
        routes=["Skilled Worker"],
        active=True,
        raw_record=[],
    )
    session.add_all([source, version, sponsor, similar_sponsor])
    session.commit()
    return session


def test_sponsor_register_returns_only_an_exact_source_name():
    session = sponsor_session()
    results, context = search_sponsor_records(session, "Northstar Labs Ltd", limit=5)
    assert context is not None
    assert [result.organisation_name for result in results] == ["Northstar Labs Ltd"]
    assert results[0].routes == ["Scale-up", "Skilled Worker"]


def test_exact_sponsor_search_is_case_insensitive():
    session = sponsor_session()
    results, _ = search_sponsor_records(session, "NORTHSTAR LABS LTD", limit=5)
    assert [result.organisation_name for result in results] == ["Northstar Labs Ltd"]


def test_partial_or_similar_sponsor_names_are_not_returned():
    session = sponsor_session()
    partial, _ = search_sponsor_records(session, "Northstar", limit=5)
    similar, _ = search_sponsor_records(session, "Northstar Lab Ltd", limit=5)
    expanded_suffix, _ = search_sponsor_records(session, "Northstar Labs Limited", limit=5)
    assert partial == []
    assert similar == []
    assert expanded_suffix == []


def test_sponsor_suggestions_use_literal_stored_name_fragments_only():
    session = sponsor_session()
    partial, _ = suggest_sponsor_records(session, "Northstar", limit=5)
    typo, _ = suggest_sponsor_records(session, "Northstor", limit=5)
    expanded_suffix, _ = suggest_sponsor_records(session, "Northstar Labs Limited", limit=5)
    assert [result.organisation_name for result in partial] == [
        "Northstar Arts CIO",
        "Northstar Labs Ltd",
    ]
    assert typo == []
    assert expanded_suffix == []


def test_exact_name_excludes_longer_lookalikes():
    session = sponsor_session()
    session.add_all(
        [
            SponsorRecord(
                dataset_version_id="version-1",
                source_record_key="d" * 64,
                organisation_name="Revolut Ltd",
                normalised_name="revolut limited",
                town_city="London",
                county=None,
                sponsor_rating="Worker (A rating)",
                routes=["Skilled Worker"],
                active=True,
                raw_record=[],
            ),
            SponsorRecord(
                dataset_version_id="version-1",
                source_record_key="e" * 64,
                organisation_name="Revolution Energy Services",
                normalised_name="revolution energy services",
                town_city="Tonbridge",
                county="Kent",
                sponsor_rating="Worker (A rating)",
                routes=["Skilled Worker"],
                active=True,
                raw_record=[],
            ),
        ]
    )
    session.commit()
    results, _ = search_sponsor_records(session, "Revolut Ltd", limit=10)
    assert [result.organisation_name for result in results] == ["Revolut Ltd"]


def test_sponsor_record_detail_is_limited_to_latest_version():
    session = sponsor_session()
    results, _ = search_sponsor_records(session, "Northstar Labs Ltd", limit=5)
    detail = get_sponsor_record(session, results[0].id)
    assert detail is not None
    assert detail.source.health == "healthy"
