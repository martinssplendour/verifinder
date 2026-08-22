from __future__ import annotations

import re
from difflib import SequenceMatcher

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.models import (
    DataSource,
    DatasetVersion,
    QualificationExpansionRecord,
    QualificationRecord,
    QualificationUnitMapping,
    QualificationUnitRecord,
    RunStatus,
)
from app.schemas import QualificationRecordView, QualificationSearchResult, QualificationUnitView, SourceAttribution
from app.services.dataset_utils import normalise_identifier
from app.services.normalization import normalise_name
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


def _ofqual_view(record: QualificationRecord, source: SourceAttribution) -> QualificationSearchResult:
    return QualificationSearchResult(
        id=record.id,
        qualification_number=record.qualification_number,
        title=record.title,
        awarding_organisation_name=record.awarding_organisation_name,
        awarding_organisation_acronym=record.awarding_organisation_acronym,
        level=record.level,
        qualification_type=record.qualification_type,
        status=record.status,
        record_type="ofqual",
        regulator="Ofqual / CCEA Regulation",
        jurisdiction="England and Northern Ireland",
        source=source,
    )


def _qiw_view(record: QualificationExpansionRecord, source: SourceAttribution) -> QualificationSearchResult:
    return QualificationSearchResult(
        id=str(record.id),
        qualification_number=record.qualification_number or record.approval_number or record.source_record_key,
        title=record.title,
        awarding_organisation_name=record.awarding_organisation_name or "Not stated",
        level=record.level,
        qualification_type=record.qualification_type,
        status=record.status,
        record_type="qiw",
        regulator=record.regulator,
        jurisdiction=record.jurisdiction,
        source=source,
    )


def _search_ofqual(
    session: Session, context: QualificationContext, query: str, limit: int
) -> list[QualificationSearchResult]:
    _, version = context
    name_query = normalise_name(query)
    number_query = normalise_identifier(query)
    candidates: list[QualificationRecord] = []
    seen: set[str] = set()

    def add(records) -> None:
        for record in records:
            if record.id not in seen:
                seen.add(record.id)
                candidates.append(record)

    exact_number = session.scalar(
        select(QualificationRecord)
        .where(
            QualificationRecord.dataset_version_id == version.id,
            QualificationRecord.normalised_number == number_query,
        )
        .limit(1)
    )
    if exact_number is not None:
        return [_ofqual_view(exact_number, _source(context))]

    looks_like_number = " " not in query.strip() and any(character.isdigit() for character in query)
    if looks_like_number:
        return []

    add(
        session.scalars(
            select(QualificationRecord)
            .where(
                QualificationRecord.dataset_version_id == version.id,
                QualificationRecord.normalised_title >= name_query,
                QualificationRecord.normalised_title < f"{name_query}\uffff",
            )
            .limit(200)
        )
    )
    tokens = [token for token in name_query.split() if len(token) > 1 or token.isdigit()]
    if len(candidates) < limit and tokens:
        token_conditions = [QualificationRecord.normalised_title.contains(token) for token in tokens]
        level_match = re.search(r"\blevel\s+(\d+)\b", query, flags=re.IGNORECASE)
        if level_match:
            token_conditions.append(QualificationRecord.level == f"Level {level_match.group(1)}")
        add(
            session.scalars(
                select(QualificationRecord)
                .where(QualificationRecord.dataset_version_id == version.id, and_(*token_conditions))
                .limit(400)
            )
        )
    if len(candidates) < limit:
        add(
            session.scalars(
                select(QualificationRecord)
                .where(
                    QualificationRecord.dataset_version_id == version.id,
                    QualificationRecord.awarding_organisation_name.ilike(f"%{query.strip()}%"),
                )
                .limit(200)
            )
        )

    def score(record: QualificationRecord) -> float:
        if record.normalised_title == name_query:
            return 0.99
        if record.normalised_title.startswith(name_query):
            return 0.96
        if name_query in record.normalised_title:
            return 0.91
        if tokens and all(token in record.normalised_title for token in tokens):
            similarity = SequenceMatcher(None, name_query, record.normalised_title).ratio()
            available_bonus = 0.025 if (record.status or "").lower() == "available to learners" else 0.0
            return 0.8 + (0.15 * similarity) + available_bonus
        if query.strip().lower() in record.awarding_organisation_name.lower():
            return 0.82
        return SequenceMatcher(None, name_query, record.normalised_title).ratio()

    ranked = sorted(candidates, key=lambda record: (-score(record), record.title.lower()))[:limit]
    source = _source(context)
    return [_ofqual_view(record, source) for record in ranked]


def _search_qiw(
    session: Session, context: QualificationContext, query: str, limit: int
) -> list[QualificationSearchResult]:
    _, version = context
    name_query = normalise_name(query)
    number_query = normalise_identifier(query)
    candidates: list[QualificationExpansionRecord] = []
    seen: set[int] = set()

    def add(records) -> None:
        for record in records:
            if record.id not in seen:
                seen.add(record.id)
                candidates.append(record)

    add(
        session.scalars(
            select(QualificationExpansionRecord)
            .where(
                QualificationExpansionRecord.dataset_version_id == version.id,
                or_(
                    QualificationExpansionRecord.normalised_number == number_query,
                    QualificationExpansionRecord.approval_number == query.strip(),
                ),
            )
            .limit(10)
        )
    )
    looks_like_number = " " not in query.strip() and any(character.isdigit() for character in query)
    tokens = [token for token in name_query.split() if len(token) > 1 or token.isdigit()]
    if not looks_like_number:
        add(
            session.scalars(
                select(QualificationExpansionRecord)
                .where(
                    QualificationExpansionRecord.dataset_version_id == version.id,
                    QualificationExpansionRecord.normalised_title >= name_query,
                    QualificationExpansionRecord.normalised_title < f"{name_query}\uffff",
                )
                .limit(200)
            )
        )
        if len(candidates) < limit and tokens:
            add(
                session.scalars(
                    select(QualificationExpansionRecord)
                    .where(
                        QualificationExpansionRecord.dataset_version_id == version.id,
                        and_(*(QualificationExpansionRecord.normalised_title.contains(token) for token in tokens)),
                    )
                    .limit(400)
                )
            )
        if len(candidates) < limit:
            add(
                session.scalars(
                    select(QualificationExpansionRecord)
                    .where(
                        QualificationExpansionRecord.dataset_version_id == version.id,
                        QualificationExpansionRecord.normalised_organisation_name.contains(name_query),
                    )
                    .limit(200)
                )
            )

    def score(record: QualificationExpansionRecord) -> float:
        if record.normalised_number == number_query or record.approval_number == query.strip():
            return 1.0
        if record.normalised_title == name_query:
            return 0.99
        if record.normalised_title.startswith(name_query):
            return 0.96
        if name_query in record.normalised_title:
            return 0.91
        if tokens and all(token in record.normalised_title for token in tokens):
            return 0.8 + (0.15 * SequenceMatcher(None, name_query, record.normalised_title).ratio())
        if name_query and name_query in (record.normalised_organisation_name or ""):
            return 0.82
        return SequenceMatcher(None, name_query, record.normalised_title).ratio()

    ranked = sorted(candidates, key=lambda record: (-score(record), record.title.lower()))[:limit]
    source = _source(context)
    return [_qiw_view(record, source) for record in ranked]


def search_qualifications(
    session: Session, query: str, limit: int = 10
) -> tuple[list[QualificationSearchResult], QualificationContext | None]:
    ofqual_context = latest_qualification_context(session)
    qiw_context = latest_welsh_qualification_context(session)
    results: list[QualificationSearchResult] = []
    if ofqual_context:
        results.extend(_search_ofqual(session, ofqual_context, query, limit))
    if qiw_context:
        results.extend(_search_qiw(session, qiw_context, query, limit))
    return results, ofqual_context or qiw_context


def _unit_details(session: Session, qualification_number: str) -> tuple[int, list[QualificationUnitView]]:
    context = latest_qualification_unit_context(session)
    if not context:
        return 0, []
    _, version = context
    normalised_number = normalise_identifier(qualification_number)
    join_condition = and_(
        QualificationUnitRecord.dataset_version_id == QualificationUnitMapping.dataset_version_id,
        QualificationUnitRecord.unit_key == QualificationUnitMapping.unit_key,
    )
    filters = (
        QualificationUnitMapping.dataset_version_id == version.id,
        QualificationUnitMapping.normalised_qualification_number == normalised_number,
    )
    count = session.scalar(
        select(func.count())
        .select_from(QualificationUnitMapping)
        .join(QualificationUnitRecord, join_condition)
        .where(*filters)
    ) or 0
    records = session.scalars(
        select(QualificationUnitRecord)
        .join(QualificationUnitMapping, join_condition)
        .where(*filters)
        .order_by(QualificationUnitRecord.title)
        .limit(100)
    )
    return int(count), [
        QualificationUnitView(
            unit_reference=record.unit_reference,
            title=record.title,
            level=record.level,
            credit_value=record.credit_value,
            guided_learning_hours=record.guided_learning_hours,
        )
        for record in records
    ]


def get_qualification(session: Session, record_id: str) -> QualificationRecordView | None:
    context = latest_qualification_context(session)
    if context:
        _, version = context
        record = session.scalar(
            select(QualificationRecord).where(
                QualificationRecord.id == record_id,
                QualificationRecord.dataset_version_id == version.id,
            )
        )
        if record is not None:
            base = _ofqual_view(record, _source(context)).model_dump()
            unit_count, units = _unit_details(session, record.qualification_number)
            return QualificationRecordView(
                **base,
                sector_subject_area=record.sector_subject_area,
                regulation_start_date=record.regulation_start_date,
                operational_start_date=record.operational_start_date,
                operational_end_date=record.operational_end_date,
                certification_end_date=record.certification_end_date,
                total_credits=record.total_credits,
                total_qualification_time=record.total_qualification_time,
                guided_learning_hours=record.guided_learning_hours,
                offered_in_england=record.offered_in_england,
                offered_in_northern_ireland=record.offered_in_northern_ireland,
                grading_type=record.grading_type,
                assessment_methods=record.assessment_methods,
                specification_url=record.specification_url,
                unit_count=unit_count,
                units=units,
            )
    qiw_context = latest_welsh_qualification_context(session)
    if not qiw_context:
        return None
    try:
        numeric_id = int(record_id)
    except ValueError:
        return None
    _, version = qiw_context
    record = session.scalar(
        select(QualificationExpansionRecord).where(
            QualificationExpansionRecord.id == numeric_id,
            QualificationExpansionRecord.dataset_version_id == version.id,
        )
    )
    if record is None:
        return None
    base = _qiw_view(record, _source(qiw_context)).model_dump()
    return QualificationRecordView(
        **base,
        operational_start_date=record.start_date,
        operational_end_date=record.end_date,
        certification_end_date=record.certification_end_date,
        approval_number=record.approval_number,
        languages=record.languages or [],
        review_type=record.review_type,
        eligible_public_funding=record.eligible_public_funding,
    )
