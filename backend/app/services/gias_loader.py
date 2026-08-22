from __future__ import annotations

from datetime import date, datetime, time, timezone

from sqlalchemy import insert, select

from app.database import SessionLocal
from app.models import DataSource, DatasetVersion, IngestionRun, RunStatus, SchoolRecord, SourceHealth
from app.services.dataset_utils import chunks
from app.services.gias_ingestion import GiasSnapshot, gias_rows


SOURCE_ID = "gias-establishments"
OFFICIAL_URL = "https://www.get-information-schools.service.gov.uk/"
DATA_URL = "https://ea-edubase-api-prod.azurewebsites.net/edubase/downloads/public/"


def _ensure_source(session, retrieved_at: datetime) -> DataSource:
    source = session.get(DataSource, SOURCE_ID)
    if source is None:
        source = DataSource(
            id=SOURCE_ID,
            organisation="Department for Education",
            name="Get Information about Schools (GIAS) establishment register",
            source_type="CSV",
            official_url=OFFICIAL_URL,
            data_url=DATA_URL,
            country="GB",
            refresh_frequency="Checked daily",
            health=SourceHealth.UNAVAILABLE,
        )
        session.add(source)
    source.last_successful_retrieval = retrieved_at
    return source


def load_gias_snapshot(snapshot: GiasSnapshot, retrieved_at: datetime, published_on: date | None = None) -> dict:
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
            version_identifier=f"{published_on.isoformat() if published_on else retrieved_at.date().isoformat()}-{snapshot.file_hash[:12]}",
            retrieved_at=retrieved_at,
            published_at=published_at,
            file_hash=snapshot.file_hash,
            record_count=snapshot.record_count,
            storage_location=str(snapshot.path),
            processing_status=RunStatus.RUNNING,
        )
        session.add(version)
        session.flush()
        run.dataset_version_id = version.id
        session.commit()

        inserted = 0
        for batch in chunks(gias_rows(snapshot, version.id), size=2_000):
            session.execute(insert(SchoolRecord), batch)
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
