from __future__ import annotations

from datetime import date, datetime, time, timezone

from sqlalchemy import insert, select

from app.database import SessionLocal
from app.models import DataSource, DatasetVersion, IngestionRun, OfsProviderRecord, RunStatus, SourceHealth, StudentSponsorRecord
from app.services.dataset_utils import chunks
from app.services.study_ingestion import OfsSnapshot, StudentSponsorSnapshot, ofs_provider_rows, student_sponsor_rows


STUDENT_SOURCE_ID = "home-office-student-sponsors"
STUDENT_OFFICIAL_URL = "https://www.gov.uk/government/publications/register-of-licensed-sponsors-students"
STUDENT_DATA_URL = "https://assets.publishing.service.gov.uk/media/6a880c5bebba21482c58cbfc/SP_-_Student_and_Child_Student_Web_Register_-_2026-08-21.csv"
OFS_SOURCE_ID = "office-for-students-register"
OFS_OFFICIAL_URL = "https://www.officeforstudents.org.uk/for-providers/registering-with-the-ofs/guide-to-the-ofs-register/"
OFS_DATA_URL = "https://register-api.officeforstudents.org.uk/api/Download/"


def _ensure_source(session, source_id: str, retrieved_at: datetime) -> DataSource:
    source = session.get(DataSource, source_id)
    if source is None:
        is_student = source_id == STUDENT_SOURCE_ID
        source = DataSource(
            id=source_id,
            organisation="UK Visas and Immigration" if is_student else "Office for Students",
            name="Register of licensed sponsors: students" if is_student else "Register of English higher education providers",
            source_type="CSV" if is_student else "XLSX",
            official_url=STUDENT_OFFICIAL_URL if is_student else OFS_OFFICIAL_URL,
            data_url=STUDENT_DATA_URL if is_student else OFS_DATA_URL,
            country="GB" if is_student else "GB",
            refresh_frequency="Checked daily" if is_student else "Checked weekly",
            health=SourceHealth.UNAVAILABLE,
        )
        session.add(source)
    source.last_successful_retrieval = retrieved_at
    return source


def _load(source_id, snapshot, model, rows, retrieved_at: datetime, published_on: date | None) -> dict:
    session = SessionLocal()
    run: IngestionRun | None = None
    version: DatasetVersion | None = None
    try:
        source = _ensure_source(session, source_id, retrieved_at)
        existing = session.scalar(select(DatasetVersion).where(DatasetVersion.file_hash == snapshot.file_hash))
        if existing:
            run = IngestionRun(
                source_id=source_id, dataset_version_id=existing.id, started_at=retrieved_at,
                finished_at=datetime.now(timezone.utc), status=RunStatus.UNCHANGED,
                records_processed=existing.record_count,
            )
            source.health = SourceHealth.HEALTHY
            session.add(run)
            session.commit()
            return {"processing_status": "unchanged", "dataset_version_id": existing.id, "record_count": existing.record_count}
        run = IngestionRun(source_id=source_id, started_at=retrieved_at, status=RunStatus.RUNNING)
        session.add(run)
        session.flush()
        published_at = datetime.combine(published_on, time.min, tzinfo=timezone.utc) if published_on else None
        version = DatasetVersion(
            source_id=source_id,
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
        for batch in chunks(rows(snapshot.path if source_id == STUDENT_SOURCE_ID else snapshot, version.id), size=2_000):
            session.execute(insert(model), batch)
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
        source = _ensure_source(session, source_id, retrieved_at)
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


def load_student_sponsors(snapshot: StudentSponsorSnapshot, retrieved_at: datetime, published_on: date | None = None) -> dict:
    return _load(STUDENT_SOURCE_ID, snapshot, StudentSponsorRecord, student_sponsor_rows, retrieved_at, published_on)


def load_ofs_register(snapshot: OfsSnapshot, retrieved_at: datetime, published_on: date | None = None) -> dict:
    return _load(OFS_SOURCE_ID, snapshot, OfsProviderRecord, ofs_provider_rows, retrieved_at, published_on)
