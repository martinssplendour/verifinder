from __future__ import annotations

from difflib import SequenceMatcher

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.models import QualificationExpansionRecord
from app.schemas import QualificationSearchResult, SourceAttribution
from app.services.dataset_utils import normalise_identifier
from app.services.normalization import normalise_name

from .shared import QualificationContext, _source


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
                    QualificationExpansionRecord.normalised_title < f"{name_query}￿",
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
