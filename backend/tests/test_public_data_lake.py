from datetime import datetime, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.database import Base
from app.models import DataSource, DatasetVersion, RunStatus, SourceHealth, SponsorRecord
from app.public_data_lake import (
    PUBLIC_TABLES,
    activate_snapshot,
    export_sqlite_to_parquet,
    verify_snapshot,
)
from app.services.sponsor_lookup import search_sponsor_records


def _source_database(path):
    engine = create_engine(f"sqlite:///{path.as_posix()}")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        source = DataSource(
            id="home-office-worker-sponsors",
            organisation="UK Visas and Immigration",
            name="Register of licensed sponsors: workers",
            source_type="CSV",
            official_url="https://www.gov.uk/government/publications/register-of-licensed-sponsors-workers",
            country="GB",
            health=SourceHealth.HEALTHY,
        )
        version = DatasetVersion(
            id="version-1",
            source_id=source.id,
            version_identifier="test-release",
            retrieved_at=datetime.now(timezone.utc),
            file_hash="a" * 64,
            record_count=1,
            storage_location="source.csv",
            processing_status=RunStatus.SUCCEEDED,
        )
        record = SponsorRecord(
            id="sponsor-1",
            dataset_version_id=version.id,
            source_record_key="record-1",
            organisation_name="Revolut Ltd",
            normalised_name="revolut ltd",
            town_city="London",
            sponsor_rating="Worker (A rating)",
            routes=["Skilled Worker"],
            active=True,
            raw_record={"Organisation Name": "Revolut Ltd"},
        )
        session.add_all([source, version, record])
        session.commit()


def test_exports_verifies_and_queries_public_snapshot(tmp_path):
    source = tmp_path / "source.sqlite3"
    root = tmp_path / "lake"
    catalog = root / "verifinder.duckdb"
    _source_database(source)

    manifest = export_sqlite_to_parquet(source, root)

    assert set(manifest["tables"]) == set(PUBLIC_TABLES)
    assert manifest["snapshot_id"].endswith("Z")
    assert manifest["tables"]["sponsor_records"]["rows"] == 1
    assert verify_snapshot(root)["sponsor_records"] == 1
    activate_snapshot(root, catalog)

    engine = create_engine(f"duckdb:///{catalog.as_posix()}", connect_args={"read_only": True})
    with Session(engine) as session:
        stored = session.scalar(select(SponsorRecord).where(SponsorRecord.id == "sponsor-1"))
        assert stored is not None
        assert stored.organisation_name == "Revolut Ltd"
        results, context = search_sponsor_records(session, "Revolut", limit=10)

    assert context is not None
    assert [result.organisation_name for result in results] == ["Revolut Ltd"]


def test_export_rejects_incomplete_sqlite_source(tmp_path):
    source = tmp_path / "incomplete.sqlite3"
    source.touch()

    try:
        export_sqlite_to_parquet(source, tmp_path / "lake")
    except RuntimeError as error:
        assert "missing required tables" in str(error)
    else:
        raise AssertionError("Expected an incomplete SQLite source to be rejected.")
