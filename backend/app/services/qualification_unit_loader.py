from __future__ import annotations

import json
from datetime import date, datetime, time, timezone

from sqlalchemy import insert, select

from app.database import SessionLocal
from app.models import (
    DataSource,
    DatasetVersion,
    IngestionRun,
    QualificationUnitMapping,
    QualificationUnitRecord,
    RunStatus,
    SourceHealth,
)
from app.services.dataset_utils import chunks
from app.services.qualification_unit_ingestion import QualificationUnitSnapshot, unit_mapping_rows, unit_rows


SOURCE_ID = "ofqual-qualification-units"
OFFICIAL_URL = "https://www.gov.uk/find-a-regulated-qualification"
DATA_URL = "https://downloads.find-a-qualification.services.ofqual.gov.uk/extracts/Units.csv"


def _ensure_source(session, retrieved_at: datetime) -> DataSource:
    source = session.get(DataSource, SOURCE_ID)
    if source is None:
        source = DataSource(
            id=SOURCE_ID,
            organisation="Ofqual",
            name="Qualification units and qualification-unit mappings",
            source_type="CSV",
            official_url=OFFICIAL_URL,
            data_url=DATA_URL,
            country="GB",
            refresh_frequency="Checked weekly",
            health=SourceHealth.UNAVAILABLE,
        )
        session.add(source)
    source.last_successful_retrieval = retrieved_at
    return source


def load_qualification_units(snapshot: QualificationUnitSnapshot, retrieved_at: datetime, published_on: date | None = None) -> dict:
    session = SessionLocal()
    run: IngestionRun | None = None
    version: DatasetVersion | None = None
    try:
        source = _ensure_source(session, retrieved_at)
        existing = session.scalar(select(DatasetVersion).where(DatasetVersion.file_hash == snapshot.file_hash))
        if existing and existing.processing_status == RunStatus.SUCCEEDED:
            run = IngestionRun(
                source_id=SOURCE_ID, dataset_version_id=existing.id, started_at=retrieved_at,
                finished_at=datetime.now(timezone.utc), status=RunStatus.UNCHANGED,
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
        version = existing or DatasetVersion(source_id=SOURCE_ID, file_hash=snapshot.file_hash)
        version.version_identifier = f"{published_on.isoformat() if published_on else retrieved_at.date().isoformat()}-{snapshot.file_hash[:12]}"
        version.retrieved_at = retrieved_at
        version.published_at = published_at
        version.record_count = snapshot.record_count
        version.storage_location = json.dumps({"units": str(snapshot.units_path), "mappings": str(snapshot.mappings_path)})
        version.processing_status = RunStatus.RUNNING
        if existing is None:
            session.add(version)
        session.flush()
        run.dataset_version_id = version.id
        session.commit()
        inserted = 0
        for batch in chunks(unit_rows(snapshot, version.id), size=10_000):
            session.execute(insert(QualificationUnitRecord), batch)
            inserted += len(batch)
        for batch in chunks(unit_mapping_rows(snapshot, version.id), size=10_000):
            session.execute(insert(QualificationUnitMapping), batch)
            inserted += len(batch)
        version.record_count = inserted
        version.processing_status = RunStatus.SUCCEEDED
        run.status = RunStatus.SUCCEEDED
        run.finished_at = datetime.now(timezone.utc)
        run.records_processed = inserted
        run.records_added = inserted
        source.health = SourceHealth.HEALTHY
        session.commit()
        return {
            "processing_status": "succeeded",
            "dataset_version_id": version.id,
            "record_count": inserted,
            "unit_count": snapshot.unit_count,
            "mapping_count": snapshot.mapping_count,
        }
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
