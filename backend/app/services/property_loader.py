from __future__ import annotations

from datetime import date, datetime, time, timezone

from sqlalchemy import insert, select

from app.database import SessionLocal
from app.models import DataSource, DatasetVersion, IngestionRun, PropertySaleRecord, RunStatus, SourceHealth
from app.services.dataset_utils import chunks
from app.services.property_ingestion import PropertySnapshot, property_rows


SOURCE_ID = "hm-land-registry-price-paid"
OFFICIAL_URL = "https://www.gov.uk/government/statistical-data-sets/price-paid-data-downloads"
DATA_URL = "https://price-paid-data.publicdata.landregistry.gov.uk/"


def _ensure_source(session, retrieved_at: datetime) -> DataSource:
    source = session.get(DataSource, SOURCE_ID)
    if source is None:
        source = DataSource(
            id=SOURCE_ID,
            organisation="HM Land Registry",
            name="Price Paid Data (2025–2026 snapshot)",
            source_type="CSV",
            official_url=OFFICIAL_URL,
            data_url=DATA_URL,
            country="GB",
            refresh_frequency="Monthly",
            health=SourceHealth.UNAVAILABLE,
        )
        session.add(source)
    source.last_successful_retrieval = retrieved_at
    return source


def load_property_snapshot(snapshot: PropertySnapshot, retrieved_at: datetime, published_on: date | None = None) -> dict:
    session = SessionLocal()
    run: IngestionRun | None = None
    version: DatasetVersion | None = None
    try:
        source = _ensure_source(session, retrieved_at)
        existing = session.scalar(select(DatasetVersion).where(DatasetVersion.file_hash == snapshot.file_hash))
        if existing:
            run = IngestionRun(
                source_id=SOURCE_ID,
                dataset_version_id=existing.id,
                started_at=retrieved_at,
                finished_at=datetime.now(timezone.utc),
                status=RunStatus.UNCHANGED,
                records_processed=existing.record_count,
            )
            source.health = SourceHealth.HEALTHY
            session.add(run)
            session.commit()
            return {"processing_status": "unchanged", "dataset_version_id": existing.id, "record_count": existing.record_count}

        run = IngestionRun(source_id=SOURCE_ID, started_at=retrieved_at, status=RunStatus.RUNNING)
        session.add(run)
        session.flush()
        published_at = datetime.combine(published_on, time.min, tzinfo=timezone.utc) if published_on else None
        version = DatasetVersion(
            source_id=SOURCE_ID,
            version_identifier=f"2025-2026-{published_on.isoformat() if published_on else retrieved_at.date().isoformat()}-{snapshot.file_hash[:12]}",
            retrieved_at=retrieved_at,
            published_at=published_at,
            file_hash=snapshot.file_hash,
            record_count=snapshot.record_count,
            storage_location=";".join(str(path) for path in snapshot.paths),
            processing_status=RunStatus.RUNNING,
        )
        session.add(version)
        session.flush()
        run.dataset_version_id = version.id
        session.commit()

        inserted = 0
        for batch in chunks(property_rows(snapshot, version.id), size=10_000):
            session.execute(insert(PropertySaleRecord), batch)
            inserted += len(batch)

        version.record_count = inserted
        version.processing_status = RunStatus.SUCCEEDED
        run.status = RunStatus.SUCCEEDED
        run.finished_at = datetime.now(timezone.utc)
        run.records_processed = inserted
        run.records_added = inserted
        source.health = SourceHealth.HEALTHY
        session.commit()
        return {"processing_status": "succeeded", "dataset_version_id": version.id, "record_count": inserted}
    except Exception as error:
        session.rollback()
        source = _ensure_source(session, retrieved_at)
        source.health = SourceHealth.INGESTION_FAILED
        if version and (persisted_version := session.get(DatasetVersion, version.id)):
            persisted_version.processing_status = RunStatus.FAILED
        if run and (persisted_run := session.get(IngestionRun, run.id)):
            persisted_run.status = RunStatus.FAILED
            persisted_run.finished_at = datetime.now(timezone.utc)
            persisted_run.error_message = str(error)[:4000]
        session.commit()
        raise
    finally:
        session.close()
