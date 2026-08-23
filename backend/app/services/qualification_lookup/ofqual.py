from __future__ import annotations

import re
from difflib import SequenceMatcher

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.models import QualificationRecord
from app.schemas import QualificationSearchResult, SourceAttribution
from app.services.dataset_utils import normalise_identifier
from app.services.normalization import normalise_name

from .shared import QualificationContext, _source


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
                QualificationRecord.normalised_title < f"{name_query}￿",
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
