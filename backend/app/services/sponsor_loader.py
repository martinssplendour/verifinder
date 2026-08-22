from datetime import date, datetime, time, timezone
from pathlib import Path
from typing import Iterable

from sqlalchemy import insert, select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import (
    ChangeEvent,
    DataSource,
    DatasetVersion,
    IngestionRun,
    RunStatus,
    SourceHealth,
    SponsorRecord,
)
from app.services.sponsor_ingestion import SponsorSnapshot, diff_snapshots, snapshot_from_records


SOURCE_ID = "home-office-worker-sponsors"
OFFICIAL_URL = "https://www.gov.uk/government/publications/register-of-licensed-sponsors-workers"


def _chunks(items: list[dict], size: int = 2_000) -> Iterable[list[dict]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]


def _fact_payload(record: dict | None) -> dict | None:
    if record is None:
        return None
    return {
        "organisation_name": record["organisation_name"],
        "town_city": record.get("town_city"),
        "county": record.get("county"),
        "sponsor_rating": record.get("sponsor_rating"),
        "routes": sorted(record.get("routes") or []),
    }


def _change_type(previous: dict, current: dict) -> str:
    if sorted(previous.get("routes") or []) != sorted(current.get("routes") or []):
        return "route_changed"
    if previous.get("sponsor_rating") != current.get("sponsor_rating"):
        return "rating_changed"
    return "organisation_changed"


def _ensure_source(session: Session, retrieved_at: datetime) -> DataSource:
    source = session.get(DataSource, SOURCE_ID)
    if source is None:
        source = DataSource(
            id=SOURCE_ID,
            organisation="UK Visas and Immigration",
            name="Register of licensed sponsors: workers",
            source_type="CSV",
            official_url=OFFICIAL_URL,
            data_url=OFFICIAL_URL,
            country="GB",
            refresh_frequency="Checked daily",
            health=SourceHealth.UNAVAILABLE,
        )
        session.add(source)
    source.last_successful_retrieval = retrieved_at
    return source


def load_snapshot(
    snapshot: SponsorSnapshot,
    storage_location: Path,
    retrieved_at: datetime,
    published_on: date | None = None,
) -> dict:
    """Load a validated snapshot atomically and keep failed/unchanged run history."""
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
                records_processed=len(snapshot.records),
            )
            source.health = SourceHealth.HEALTHY
            session.add(run)
            session.commit()
            return {
                "processing_status": "unchanged",
                "dataset_version_id": existing.id,
                "record_count": existing.record_count,
                "records_added": 0,
                "records_removed": 0,
                "records_changed": 0,
            }

        previous_version = session.scalar(
            select(DatasetVersion)
            .where(
                DatasetVersion.source_id == SOURCE_ID,
                DatasetVersion.processing_status == RunStatus.SUCCEEDED,
            )
            .order_by(DatasetVersion.retrieved_at.desc())
            .limit(1)
        )
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
            record_count=len(snapshot.records),
            storage_location=str(storage_location),
            processing_status=RunStatus.RUNNING,
        )
        session.add(version)
        session.flush()
        run.dataset_version_id = version.id
        session.commit()

        rows = [
            {
                "dataset_version_id": version.id,
                "source_record_key": key,
                "organisation_name": record["organisation_name"],
                "normalised_name": record["normalised_name"],
                "town_city": record.get("town_city"),
                "county": record.get("county"),
                "sponsor_rating": record.get("sponsor_rating"),
                "routes": sorted(record.get("routes") or []),
                "active": True,
                "raw_record": record.get("raw_records") or [],
            }
            for key, record in snapshot.records.items()
        ]
        for batch in _chunks(rows):
            session.execute(insert(SponsorRecord), batch)

        if previous_version:
            previous_rows = list(
                session.scalars(
                    select(SponsorRecord).where(SponsorRecord.dataset_version_id == previous_version.id)
                )
            )
            previous_snapshot = snapshot_from_records(previous_rows)
            changes = diff_snapshots(previous_snapshot, snapshot)
        else:
            previous_snapshot = SponsorSnapshot(file_hash="none", records={}, columns={})
            changes = None

        event_rows: list[dict] = []
        if changes:
            for key in changes.added:
                event_rows.append(
                    {
                        "source_id": SOURCE_ID,
                        "previous_dataset_version_id": previous_version.id,
                        "current_dataset_version_id": version.id,
                        "source_record_key": key,
                        "change_type": "sponsor_added",
                        "previous_value": None,
                        "new_value": _fact_payload(snapshot.records[key]),
                        "detected_at": retrieved_at,
                    }
                )
            for key in changes.removed:
                event_rows.append(
                    {
                        "source_id": SOURCE_ID,
                        "previous_dataset_version_id": previous_version.id,
                        "current_dataset_version_id": version.id,
                        "source_record_key": key,
                        "change_type": "sponsor_removed",
                        "previous_value": _fact_payload(previous_snapshot.records[key]),
                        "new_value": None,
                        "detected_at": retrieved_at,
                    }
                )
            for key in changes.changed:
                previous = previous_snapshot.records[key]
                current = snapshot.records[key]
                event_rows.append(
                    {
                        "source_id": SOURCE_ID,
                        "previous_dataset_version_id": previous_version.id,
                        "current_dataset_version_id": version.id,
                        "source_record_key": key,
                        "change_type": _change_type(previous, current),
                        "previous_value": _fact_payload(previous),
                        "new_value": _fact_payload(current),
                        "detected_at": retrieved_at,
                    }
                )
            for batch in _chunks(event_rows):
                session.execute(insert(ChangeEvent), batch)

        added = len(changes.added) if changes else len(snapshot.records)
        removed = len(changes.removed) if changes else 0
        changed = len(changes.changed) if changes else 0
        version.processing_status = RunStatus.SUCCEEDED
        run.status = RunStatus.SUCCEEDED
        run.finished_at = datetime.now(timezone.utc)
        run.records_processed = len(snapshot.records)
        run.records_added = added
        run.records_removed = removed
        run.records_changed = changed
        source.health = SourceHealth.HEALTHY
        source.last_successful_retrieval = retrieved_at
        session.commit()
        return {
            "processing_status": "succeeded",
            "dataset_version_id": version.id,
            "record_count": len(snapshot.records),
            "records_added": added,
            "records_removed": removed,
            "records_changed": changed,
        }
    except Exception as error:
        session.rollback()
        try:
            source = _ensure_source(session, retrieved_at)
            source.health = SourceHealth.INGESTION_FAILED
            if version:
                persisted_version = session.get(DatasetVersion, version.id)
                if persisted_version:
                    persisted_version.processing_status = RunStatus.FAILED
            if run:
                persisted_run = session.get(IngestionRun, run.id)
                if persisted_run:
                    persisted_run.status = RunStatus.FAILED
                    persisted_run.finished_at = datetime.now(timezone.utc)
                    persisted_run.error_message = str(error)[:4000]
            session.commit()
        finally:
            session.close()
        raise
    finally:
        if session.is_active:
            session.close()
