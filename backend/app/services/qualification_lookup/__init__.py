from __future__ import annotations

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.models import (
    QualificationExpansionRecord,
    QualificationRecord,
    QualificationUnitMapping,
    QualificationUnitRecord,
)
from app.schemas import QualificationRecordView, QualificationSearchResult, QualificationUnitView
from app.services.dataset_utils import normalise_identifier

from .ofqual import _ofqual_view, _search_ofqual
from .qiw import _qiw_view, _search_qiw
from .shared import (
    QualificationContext,
    _source,
    latest_qualification_context,
    latest_qualification_unit_context,
    latest_welsh_qualification_context,
)

__all__ = [
    "latest_qualification_context",
    "latest_welsh_qualification_context",
    "latest_qualification_unit_context",
    "search_qualifications",
    "get_qualification",
]


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
