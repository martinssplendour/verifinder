from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import DataSource, DatasetVersion, RunStatus
from app.schemas import DecisionFact, SourceAttribution


def _latest_context(session: Session, source_id: str) -> tuple[DataSource, DatasetVersion] | None:
    row = session.execute(
        select(DataSource, DatasetVersion)
        .join(DatasetVersion, DatasetVersion.source_id == DataSource.id)
        .where(DataSource.id == source_id, DatasetVersion.processing_status == RunStatus.SUCCEEDED)
        .order_by(DatasetVersion.retrieved_at.desc())
        .limit(1)
    ).first()
    return (row[0], row[1]) if row else None


def _source(context: tuple[DataSource, DatasetVersion]) -> SourceAttribution:
    source, version = context
    return SourceAttribution(
        id=source.id,
        organisation=source.organisation,
        dataset=source.name,
        official_url=source.official_url,
        retrieved_at=version.retrieved_at,
        published_at=version.published_at,
        version=version.version_identifier,
        health=source.health.value,
    )


def _fact(label: str, value: str, kind: str = "verified_fact") -> DecisionFact:
    return DecisionFact(kind=kind, label=label, value=value)


def _count_for_location(session: Session, model, version_id: str, column, location: str) -> int:
    return int(
        session.scalar(
            select(func.count()).select_from(model).where(model.dataset_version_id == version_id, func.lower(column).contains(location.lower()))
        )
        or 0
    )
