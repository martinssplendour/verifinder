from __future__ import annotations

from difflib import SequenceMatcher

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import DataSource, DatasetVersion, OfsProviderRecord, RunStatus, StudentSponsorRecord
from app.schemas import SourceAttribution, StudyProviderDetail, StudyProviderSearchResult
from app.services.dataset_utils import normalise_identifier
from app.services.normalization import normalise_name
from app.services.search_suggestions import (
    CANDIDATE_LIMIT,
    SUGGESTION_LIMIT,
    candidate_filter,
    rank_near_matches,
)
from app.services.study_loader import OFS_SOURCE_ID, STUDENT_SOURCE_ID


StudyContext = tuple[DataSource, DatasetVersion]


def _latest_context(session: Session, source_id: str) -> StudyContext | None:
    row = session.execute(
        select(DataSource, DatasetVersion)
        .join(DatasetVersion, DatasetVersion.source_id == DataSource.id)
        .where(DataSource.id == source_id, DatasetVersion.processing_status == RunStatus.SUCCEEDED)
        .order_by(DatasetVersion.retrieved_at.desc())
        .limit(1)
    ).first()
    return (row[0], row[1]) if row else None


def latest_student_sponsor_context(session: Session) -> StudyContext | None:
    return _latest_context(session, STUDENT_SOURCE_ID)


def latest_ofs_context(session: Session) -> StudyContext | None:
    return _latest_context(session, OFS_SOURCE_ID)


def source_attribution(context: StudyContext) -> SourceAttribution:
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


def _student_view(record: StudentSponsorRecord, source: SourceAttribution) -> StudyProviderSearchResult:
    return StudyProviderSearchResult(
        id=str(record.id),
        record_type="student_sponsor",
        name=record.organisation_name,
        town_city=record.town_city,
        provider_type=record.sponsor_type,
        status=record.status,
        routes=record.routes or [],
        source=source,
    )


def _ofs_view(record: OfsProviderRecord, source: SourceAttribution) -> StudyProviderSearchResult:
    return StudyProviderSearchResult(
        id=str(record.id),
        record_type="ofs",
        name=record.legal_name,
        provider_type=record.registration_category or "Registered higher education provider",
        status="Registered",
        ukprn=record.ukprn,
        source=source,
    )


def _ranked_student_records(
    session: Session, context: StudyContext, query: str, limit: int
) -> list[StudentSponsorRecord]:
    _, version = context
    normalised = normalise_name(query)
    candidates = list(
        session.scalars(
            select(StudentSponsorRecord)
            .where(
                StudentSponsorRecord.dataset_version_id == version.id,
                or_(
                    StudentSponsorRecord.normalised_name == normalised,
                    StudentSponsorRecord.normalised_name.startswith(normalised),
                    StudentSponsorRecord.normalised_name.contains(normalised),
                ),
            )
            .limit(max(limit * 12, 120))
        )
    )

    def score(record: StudentSponsorRecord) -> float:
        if record.normalised_name == normalised:
            return 1.0
        if record.normalised_name.startswith(normalised):
            return 0.96
        if normalised in record.normalised_name:
            return 0.9
        return SequenceMatcher(None, normalised, record.normalised_name).ratio()

    return sorted(candidates, key=lambda item: (-score(item), item.organisation_name.lower()))[:limit]


def _ranked_ofs_records(session: Session, context: StudyContext, query: str, limit: int) -> list[OfsProviderRecord]:
    _, version = context
    normalised = normalise_name(query)
    identifier = normalise_identifier(query)
    candidates = list(
        session.scalars(
            select(OfsProviderRecord)
            .where(
                OfsProviderRecord.dataset_version_id == version.id,
                or_(
                    OfsProviderRecord.ukprn == identifier,
                    OfsProviderRecord.normalised_name == normalised,
                    OfsProviderRecord.normalised_name.startswith(normalised),
                    OfsProviderRecord.normalised_name.contains(normalised),
                    OfsProviderRecord.normalised_aliases.contains(normalised),
                    OfsProviderRecord.postcode == query.strip().upper(),
                ),
            )
            .limit(max(limit * 12, 120))
        )
    )

    def score(record: OfsProviderRecord) -> float:
        aliases = [normalise_name(value) for value in (record.trading_names or [])]
        if record.ukprn == identifier or record.normalised_name == normalised or normalised in aliases:
            return 1.0
        if record.normalised_name.startswith(normalised) or any(alias.startswith(normalised) for alias in aliases):
            return 0.96
        if normalised in record.normalised_name or any(normalised in alias for alias in aliases):
            return 0.9
        return SequenceMatcher(None, normalised, record.normalised_name).ratio()

    return sorted(candidates, key=lambda item: (-score(item), item.legal_name.lower()))[:limit]


def search_study_providers(
    session: Session, query: str, limit: int = 10
) -> tuple[list[StudyProviderSearchResult], StudyContext | None, StudyContext | None]:
    student_context = latest_student_sponsor_context(session)
    ofs_context = latest_ofs_context(session)
    results: list[StudyProviderSearchResult] = []
    per_source_limit = max(1, limit)
    if student_context:
        source = source_attribution(student_context)
        results.extend(_student_view(record, source) for record in _ranked_student_records(session, student_context, query, per_source_limit))
    if ofs_context:
        source = source_attribution(ofs_context)
        results.extend(_ofs_view(record, source) for record in _ranked_ofs_records(session, ofs_context, query, per_source_limit))
    return results, student_context, ofs_context


def similar_study_providers(
    session: Session, query: str, limit: int = SUGGESTION_LIMIT
) -> list[StudyProviderSearchResult]:
    """Close provider names to offer when neither study register matched."""
    normalised = normalise_name(query)
    results: list[StudyProviderSearchResult] = []

    student_context = latest_student_sponsor_context(session)
    if student_context:
        condition = candidate_filter(StudentSponsorRecord.normalised_name, normalised)
        if condition is not None:
            _, version = student_context
            candidates = list(
                session.scalars(
                    select(StudentSponsorRecord)
                    .where(StudentSponsorRecord.dataset_version_id == version.id, condition)
                    .limit(CANDIDATE_LIMIT)
                )
            )
            source = source_attribution(student_context)
            results.extend(
                _student_view(record, source)
                for record in rank_near_matches(candidates, normalised, lambda record: record.normalised_name, limit)
            )

    ofs_context = latest_ofs_context(session)
    if ofs_context:
        condition = candidate_filter(OfsProviderRecord.normalised_name, normalised)
        if condition is not None:
            _, version = ofs_context
            candidates = list(
                session.scalars(
                    select(OfsProviderRecord)
                    .where(OfsProviderRecord.dataset_version_id == version.id, condition)
                    .limit(CANDIDATE_LIMIT)
                )
            )
            source = source_attribution(ofs_context)
            results.extend(
                _ofs_view(record, source)
                for record in rank_near_matches(candidates, normalised, lambda record: record.normalised_name, limit)
            )

    return results[: limit * 2]


def _matching_ofs(session: Session, record: StudentSponsorRecord) -> StudyProviderSearchResult | None:
    context = latest_ofs_context(session)
    if not context:
        return None
    _, version = context
    matched = session.scalar(
        select(OfsProviderRecord).where(
            OfsProviderRecord.dataset_version_id == version.id,
            or_(
                OfsProviderRecord.normalised_name == record.normalised_name,
                OfsProviderRecord.normalised_aliases.contains(record.normalised_name),
            ),
        )
    )
    return _ofs_view(matched, source_attribution(context)) if matched else None


def _matching_student(session: Session, record: OfsProviderRecord) -> StudyProviderSearchResult | None:
    context = latest_student_sponsor_context(session)
    if not context:
        return None
    _, version = context
    names = {record.normalised_name, *(normalise_name(value) for value in (record.trading_names or []))}
    matched = session.scalar(
        select(StudentSponsorRecord).where(
            StudentSponsorRecord.dataset_version_id == version.id,
            StudentSponsorRecord.normalised_name.in_(names),
        )
    )
    return _student_view(matched, source_attribution(context)) if matched else None


def get_study_provider(session: Session, record_type: str, record_id: int) -> StudyProviderDetail | None:
    if record_type == "student_sponsor":
        context = latest_student_sponsor_context(session)
        if not context:
            return None
        _, version = context
        record = session.scalar(
            select(StudentSponsorRecord).where(
                StudentSponsorRecord.id == record_id,
                StudentSponsorRecord.dataset_version_id == version.id,
            )
        )
        if record is None:
            return None
        return StudyProviderDetail(
            **_student_view(record, source_attribution(context)).model_dump(),
            additional_locations=record.additional_locations,
            immigration_compliance=record.immigration_compliance,
            matched_record=_matching_ofs(session, record),
            limitations=[
                "A student-sponsor listing confirms permission to sponsor students; it is not academic accreditation.",
                "A missing OfS match is not evidence that a provider is unrecognised, because the OfS Register covers English higher education providers only.",
            ],
        )
    if record_type == "ofs":
        context = latest_ofs_context(session)
        if not context:
            return None
        _, version = context
        record = session.scalar(
            select(OfsProviderRecord).where(
                OfsProviderRecord.id == record_id,
                OfsProviderRecord.dataset_version_id == version.id,
            )
        )
        if record is None:
            return None
        return StudyProviderDetail(
            **_ofs_view(record, source_attribution(context)).model_dump(),
            trading_names=record.trading_names or [],
            contact_address=record.contact_address,
            postcode=record.postcode,
            email=record.email,
            website=record.website,
            charity_status=record.charity_status,
            registration_category=record.registration_category,
            fee_limits=record.fee_limits,
            tef_rating=record.tef_rating,
            degree_awarding_powers=record.degree_awarding_powers,
            degree_awarding_powers_date=record.degree_awarding_powers_date,
            university_title=record.university_title,
            university_title_date=record.university_title_date,
            university_title_basis=record.university_title_basis,
            access_plan=record.access_plan,
            access_plan_url=record.access_plan_url,
            specific_conditions=record.specific_conditions or [],
            matched_record=_matching_student(session, record),
            limitations=[
                "The OfS Register covers registered higher education providers in England.",
                "An exact-name student-sponsor match is shown only as a cross-reference; sponsorship permission and OfS registration are separate checks.",
            ],
        )
    return None
