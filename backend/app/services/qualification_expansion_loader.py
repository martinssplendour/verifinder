from __future__ import annotations

from datetime import date, datetime, time, timezone

from sqlalchemy import insert, select

from app.database import SessionLocal
from app.models import DataSource, DatasetVersion, IngestionRun, QualificationExpansionRecord, RunStatus, SourceHealth
from app.services.dataset_utils import chunks
from app.services.qualification_expansion_ingestion import WelshQualificationSnapshot, welsh_qualification_rows


QIW_SOURCE_ID = "qualifications-wales-qiw"
QIW_OFFICIAL_URL = "https://www.qiw.wales/"
QIW_DATA_URL = "https://www.qiw.wales/export/Complete/All/en"


def _ensure_source(session, retrieved_at: datetime) -> DataSource:
    source = session.get(DataSource, QIW_SOURCE_ID)
    if source is None:
        source = DataSource(
            id=QIW_SOURCE_ID,
            organisation="Qualifications Wales",
            name="Qualifications in Wales (QiW) complete register",
            source_type="CSV",
            official_url=QIW_OFFICIAL_URL,
            data_url=QIW_DATA_URL,
            country="GB",
            refresh_frequency="Checked weekly",
            health=SourceHealth.UNAVAILABLE,
        )
        session.add(source)
    source.last_successful_retrieval = retrieved_at
    return source


def load_welsh_qualifications(snapshot: WelshQualificationSnapshot, retrieved_at: datetime, published_on: date | None = None) -> dict:
    session = SessionLocal()
    run: IngestionRun | None = None
    version: DatasetVersion | None = None
    try:
        source = _ensure_source(session, retrieved_at)
        existing = session.scalar(select(DatasetVersion).where(DatasetVersion.file_hash == snapshot.file_hash))
        if existing and existing.processing_status == RunStatus.SUCCEEDED:
            run = IngestionRun(
                source_id=QIW_SOURCE_ID, dataset_version_id=existing.id, started_at=retrieved_at,
                finished_at=datetime.now(timezone.utc), status=RunStatus.UNCHANGED,
                records_processed=existing.record_count,
            )
            source.health = SourceHealth.HEALTHY
            session.add(run)
            session.commit()
            return {"processing_status": "unchanged", "dataset_version_id": existing.id, "record_count": existing.record_count}
        run = IngestionRun(source_id=QIW_SOURCE_ID, started_at=retrieved_at, status=RunStatus.RUNNING)
        session.add(run)
        session.flush()
        published_at = datetime.combine(published_on, time.min, tzinfo=timezone.utc) if published_on else None
        version = existing or DatasetVersion(source_id=QIW_SOURCE_ID, file_hash=snapshot.file_hash)
        version.version_identifier = f"{published_on.isoformat() if published_on else retrieved_at.date().isoformat()}-{snapshot.file_hash[:12]}"
        version.retrieved_at = retrieved_at
        version.published_at = published_at
        version.record_count = snapshot.record_count
        version.storage_location = str(snapshot.path)
        version.processing_status = RunStatus.RUNNING
        if existing is None:
            session.add(version)
        session.flush()
        run.dataset_version_id = version.id
        session.commit()
        inserted = 0
        for batch in chunks(welsh_qualification_rows(snapshot, version.id), size=5_000):
            session.execute(insert(QualificationExpansionRecord), batch)
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
