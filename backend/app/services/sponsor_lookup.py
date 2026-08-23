import re
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import DataSource, DatasetVersion, RunStatus, SponsorRecord
from app.schemas import SourceAttribution, SponsorRecordView
from app.services.sponsor_loader import OFFICIAL_URL, SOURCE_ID


@dataclass(frozen=True)
class SponsorContext:
    source: DataSource
    version: DatasetVersion


def latest_sponsor_context(session: Session) -> SponsorContext | None:
    version = session.scalar(
        select(DatasetVersion)
        .where(
            DatasetVersion.source_id == SOURCE_ID,
            DatasetVersion.processing_status == RunStatus.SUCCEEDED,
        )
        .order_by(DatasetVersion.retrieved_at.desc())
        .limit(1)
    )
    if version is None:
        return None
    source = session.get(DataSource, SOURCE_ID)
    if source is None:
        return None
    return SponsorContext(source=source, version=version)


def source_attribution(context: SponsorContext) -> SourceAttribution:
    return SourceAttribution(
        id=SOURCE_ID,
        organisation=context.source.organisation,
        dataset=context.source.name,
        official_url=context.source.official_url or OFFICIAL_URL,
        retrieved_at=context.version.retrieved_at,
        published_at=context.version.published_at,
        version=context.version.version_identifier,
        health=context.source.health.value,
    )


def rating_label(raw_rating: str | None) -> str | None:
    if not raw_rating:
        return None
    match = re.search(r"\(([A-Za-z]+)\s+rating\)", raw_rating, re.IGNORECASE)
    return match.group(1).upper() if match else raw_rating


def sponsor_record_view(record: SponsorRecord, context: SponsorContext) -> SponsorRecordView:
    return SponsorRecordView(
        id=record.id,
        organisation_name=record.organisation_name,
        town_city=record.town_city,
        county=record.county,
        rating=rating_label(record.sponsor_rating),
        routes=sorted(record.routes or []),
        source=source_attribution(context),
    )


def search_sponsor_records(session: Session, query: str, limit: int = 8) -> tuple[list[SponsorRecordView], SponsorContext | None]:
    context = latest_sponsor_context(session)
    if context is None:
        return [], None
    exact_name = query.strip().lower()
    if not exact_name:
        return [], context

    records = list(
        session.scalars(
            select(SponsorRecord)
            .where(
                SponsorRecord.dataset_version_id == context.version.id,
                SponsorRecord.active.is_(True),
                func.lower(func.trim(SponsorRecord.organisation_name)) == exact_name,
            )
            .order_by(SponsorRecord.organisation_name, SponsorRecord.town_city)
            .limit(limit)
        )
    )
    return [sponsor_record_view(record, context) for record in records], context


def suggest_sponsor_records(
    session: Session,
    query: str,
    limit: int = 4,
) -> tuple[list[SponsorRecordView], SponsorContext | None]:
    context = latest_sponsor_context(session)
    if context is None:
        return [], None
    fragment = query.strip().lower()
    if not fragment:
        return [], context

    candidates = list(
        session.scalars(
            select(SponsorRecord)
            .where(
                SponsorRecord.dataset_version_id == context.version.id,
                SponsorRecord.active.is_(True),
                func.lower(SponsorRecord.organisation_name).contains(fragment, autoescape=True),
            )
            .limit(max(limit * 12, 48))
        )
    )
    candidates.sort(
        key=lambda record: (
            not record.organisation_name.lower().startswith(fragment),
            record.organisation_name.lower(),
            (record.town_city or "").lower(),
        )
    )
    return [sponsor_record_view(record, context) for record in candidates[:limit]], context


def get_sponsor_record(session: Session, record_id: str) -> SponsorRecordView | None:
    context = latest_sponsor_context(session)
    if context is None:
        return None
    record = session.scalar(
        select(SponsorRecord).where(
            SponsorRecord.id == record_id,
            SponsorRecord.dataset_version_id == context.version.id,
        )
    )
    return sponsor_record_view(record, context) if record else None
