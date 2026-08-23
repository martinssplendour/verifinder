from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DataSource, DatasetVersion, RunStatus
from app.schemas import SourceAttribution
from app.services.qualification_expansion_loader import QIW_SOURCE_ID
from app.services.qualification_loader import SOURCE_ID
from app.services.qualification_unit_loader import SOURCE_ID as UNIT_SOURCE_ID


QualificationContext = tuple[DataSource, DatasetVersion]


def _latest_context(session: Session, source_id: str) -> QualificationContext | None:
    row = session.execute(
        select(DataSource, DatasetVersion)
        .join(DatasetVersion, DatasetVersion.source_id == DataSource.id)
        .where(DataSource.id == source_id, DatasetVersion.processing_status == RunStatus.SUCCEEDED)
        .order_by(DatasetVersion.retrieved_at.desc())
        .limit(1)
    ).first()
    return (row[0], row[1]) if row else None


def latest_qualification_context(session: Session) -> QualificationContext | None:
    return _latest_context(session, SOURCE_ID)


def latest_welsh_qualification_context(session: Session) -> QualificationContext | None:
    return _latest_context(session, QIW_SOURCE_ID)


def latest_qualification_unit_context(session: Session) -> QualificationContext | None:
    return _latest_context(session, UNIT_SOURCE_ID)


def _source(context: QualificationContext) -> SourceAttribution:
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
