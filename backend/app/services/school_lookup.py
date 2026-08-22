from __future__ import annotations

from difflib import SequenceMatcher

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import DataSource, DatasetVersion, OfstedInspectionRecord, RunStatus, SchoolRecord
from app.schemas import OfstedInspectionSummary, SchoolDetail, SchoolSearchResult, SourceAttribution
from app.services.dataset_utils import normalise_identifier, normalise_postcode
from app.services.gias_loader import SOURCE_ID as GIAS_SOURCE_ID
from app.services.normalization import normalise_name
from app.services.ofsted_loader import SOURCE_ID as OFSTED_SOURCE_ID


SchoolContext = tuple[DataSource, DatasetVersion]


def _latest_context(session: Session, source_id: str) -> SchoolContext | None:
    row = session.execute(
        select(DataSource, DatasetVersion)
        .join(DatasetVersion, DatasetVersion.source_id == DataSource.id)
        .where(DataSource.id == source_id, DatasetVersion.processing_status == RunStatus.SUCCEEDED)
        .order_by(DatasetVersion.retrieved_at.desc())
        .limit(1)
    ).first()
    return (row[0], row[1]) if row else None


def latest_school_context(session: Session) -> SchoolContext | None:
    return _latest_context(session, GIAS_SOURCE_ID)


def latest_ofsted_context(session: Session) -> SchoolContext | None:
    return _latest_context(session, OFSTED_SOURCE_ID)


def _attribution(context: SchoolContext) -> SourceAttribution:
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


def _search_view(record: SchoolRecord, source: SourceAttribution) -> SchoolSearchResult:
    return SchoolSearchResult(
        urn=record.urn,
        establishment_name=record.establishment_name,
        la_name=record.la_name,
        type_name=record.type_name,
        phase_name=record.phase_name,
        status_name=record.status_name,
        postcode=record.postcode,
        town=record.town,
        source=source,
    )


def _ranked_schools(session: Session, context: SchoolContext, query: str, limit: int) -> list[SchoolRecord]:
    _, version = context
    normalised = normalise_name(query)
    normalised_postcode = normalise_postcode(query)
    identifier = normalise_identifier(query)
    candidates = list(
        session.scalars(
            select(SchoolRecord)
            .where(
                SchoolRecord.dataset_version_id == version.id,
                or_(
                    SchoolRecord.urn == identifier,
                    SchoolRecord.normalised_postcode == normalised_postcode,
                    SchoolRecord.normalised_name == normalised,
                    SchoolRecord.normalised_name.startswith(normalised),
                    SchoolRecord.normalised_name.contains(normalised),
                ),
            )
            .limit(max(limit * 12, 120))
        )
    )

    def score(record: SchoolRecord) -> float:
        if record.urn == identifier or record.normalised_postcode == normalised_postcode:
            return 1.0
        if record.normalised_name == normalised:
            return 0.98
        if record.normalised_name.startswith(normalised):
            return 0.96
        if normalised in record.normalised_name:
            return 0.9
        return SequenceMatcher(None, normalised, record.normalised_name).ratio()

    return sorted(candidates, key=lambda item: (-score(item), item.establishment_name.lower()))[:limit]


def search_schools(session: Session, query: str, limit: int = 10) -> tuple[list[SchoolSearchResult], SchoolContext | None]:
    context = latest_school_context(session)
    if context is None:
        return [], None
    source = _attribution(context)
    results = [_search_view(record, source) for record in _ranked_schools(session, context, query, limit)]
    return results, context


def _ofsted_summary(session: Session, urn: str) -> OfstedInspectionSummary:
    context = latest_ofsted_context(session)
    if context is None:
        return OfstedInspectionSummary(
            status="data_unavailable",
            message="Ofsted inspection data is not connected.",
        )
    _, version = context
    record = session.scalar(
        select(OfstedInspectionRecord).where(
            OfstedInspectionRecord.dataset_version_id == version.id,
            OfstedInspectionRecord.urn == urn,
        )
    )
    if record is None:
        return OfstedInspectionSummary(
            status="data_unavailable",
            source=_attribution(context),
            message="No matching URN was found in the latest Ofsted state-funded schools extract.",
        )
    return OfstedInspectionSummary(
        status="matched",
        urn=record.urn,
        most_recent_category_of_concern=record.most_recent_category_of_concern,
        full_inspection_type=record.full_inspection_type,
        full_inspection_start_date=record.full_inspection_start_date,
        full_inspection_publication_date=record.full_inspection_publication_date,
        safeguarding_standards=record.safeguarding_standards,
        inclusion=record.inclusion,
        curriculum_and_teaching=record.curriculum_and_teaching,
        achievement=record.achievement,
        attendance_and_behaviour=record.attendance_and_behaviour,
        personal_development_and_wellbeing=record.personal_development_and_wellbeing,
        early_years=record.early_years,
        post_16_provision=record.post_16_provision,
        leadership_and_governance=record.leadership_and_governance,
        oeif_start_date=record.oeif_start_date,
        oeif_publication_date=record.oeif_publication_date,
        oeif_overall_effectiveness=record.oeif_overall_effectiveness,
        oeif_safeguarding_effective=record.oeif_safeguarding_effective,
        ungraded_inspection_date=record.ungraded_inspection_date,
        ungraded_publication_date=record.ungraded_publication_date,
        ungraded_overall_outcome=record.ungraded_overall_outcome,
        source=_attribution(context),
    )


def get_school(session: Session, urn: str) -> SchoolDetail | None:
    context = latest_school_context(session)
    if context is None:
        return None
    _, version = context
    record = session.scalar(
        select(SchoolRecord).where(SchoolRecord.dataset_version_id == version.id, SchoolRecord.urn == urn)
    )
    if record is None:
        return None
    return SchoolDetail(
        urn=record.urn,
        establishment_name=record.establishment_name,
        la_name=record.la_name,
        type_name=record.type_name,
        type_group_name=record.type_group_name,
        status_name=record.status_name,
        phase_name=record.phase_name,
        statutory_low_age=record.statutory_low_age,
        statutory_high_age=record.statutory_high_age,
        gender_name=record.gender_name,
        religious_character_name=record.religious_character_name,
        school_capacity=record.school_capacity,
        number_of_pupils=record.number_of_pupils,
        ukprn=record.ukprn,
        open_date=record.open_date,
        close_date=record.close_date,
        street=record.street,
        locality=record.locality,
        town=record.town,
        county_name=record.county_name,
        postcode=record.postcode,
        website=record.website,
        telephone=record.telephone,
        head_first_name=record.head_first_name,
        head_last_name=record.head_last_name,
        region_name=record.region_name,
        country_name=record.country_name,
        source=_attribution(context),
        ofsted=_ofsted_summary(session, record.urn),
        limitations=[
            "GIAS establishment details are the Department for Education's own register; they do not confirm current staffing, admissions decisions or in-year status changes.",
            "The Ofsted match is by exact URN; a school with no result may be independent, newly opened or awaiting its first inspection rather than unrated.",
            "Ofsted's 2025 inspection framework and the earlier single-grade framework are shown separately because they are not directly comparable.",
        ],
    )
