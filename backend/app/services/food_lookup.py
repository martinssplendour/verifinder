from __future__ import annotations

from difflib import SequenceMatcher

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.models import DataSource, DatasetVersion, FoodEstablishmentRecord, RunStatus
from app.schemas import FoodEstablishmentSearchResult, FoodEstablishmentView, SourceAttribution
from app.services.dataset_utils import normalise_postcode
from app.services.food_loader import SOURCE_ID
from app.services.normalization import normalise_name


def latest_food_context(session: Session) -> tuple[DataSource, DatasetVersion] | None:
    row = session.execute(
        select(DataSource, DatasetVersion)
        .join(DatasetVersion, DatasetVersion.source_id == DataSource.id)
        .where(DataSource.id == SOURCE_ID, DatasetVersion.processing_status == RunStatus.SUCCEEDED)
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


def _search_view(record: FoodEstablishmentRecord, source: SourceAttribution) -> FoodEstablishmentSearchResult:
    return FoodEstablishmentSearchResult(
        id=record.id,
        fhrs_id=record.fhrs_id,
        business_name=record.business_name,
        business_type=record.business_type,
        address=record.address,
        postcode=record.postcode,
        rating_value=record.rating_value,
        rating_date=record.rating_date,
        local_authority_name=record.local_authority_name,
        scheme_type=record.scheme_type,
        new_rating_pending=record.new_rating_pending,
        source=source,
    )


def search_food_establishments(
    session: Session, query: str, limit: int = 10
) -> tuple[list[FoodEstablishmentSearchResult], tuple[DataSource, DatasetVersion] | None]:
    context = latest_food_context(session)
    if not context:
        return [], None
    _, version = context
    name_query = normalise_name(query)
    postcode_query = normalise_postcode(query)
    conditions = [
        and_(
            FoodEstablishmentRecord.normalised_name >= name_query,
            FoodEstablishmentRecord.normalised_name < f"{name_query}\uffff",
        )
    ]
    if postcode_query:
        conditions.append(
            and_(
                FoodEstablishmentRecord.normalised_postcode >= postcode_query,
                FoodEstablishmentRecord.normalised_postcode < f"{postcode_query}\uffff",
            )
        )
    candidates = list(
        session.scalars(
            select(FoodEstablishmentRecord)
            .where(FoodEstablishmentRecord.dataset_version_id == version.id, or_(*conditions))
            .limit(500)
        )
    )

    def score(record: FoodEstablishmentRecord) -> float:
        if postcode_query and record.normalised_postcode == postcode_query:
            return 1.0
        if record.normalised_name == name_query:
            return 0.99
        if record.normalised_name.startswith(name_query):
            return 0.96
        if name_query in record.normalised_name:
            return 0.91
        if query.strip().lower() in (record.local_authority_name or "").lower():
            return 0.8
        return SequenceMatcher(None, name_query, record.normalised_name).ratio()

    ranked = sorted(candidates, key=lambda record: (-score(record), record.business_name.lower()))[:limit]
    source = _source(context)
    return [_search_view(record, source) for record in ranked], context


def get_food_establishment(session: Session, record_id: str) -> FoodEstablishmentView | None:
    context = latest_food_context(session)
    if not context:
        return None
    _, version = context
    record = session.scalar(
        select(FoodEstablishmentRecord).where(
            FoodEstablishmentRecord.id == record_id,
            FoodEstablishmentRecord.dataset_version_id == version.id,
        )
    )
    if record is None:
        return None
    base = _search_view(record, _source(context)).model_dump()
    return FoodEstablishmentView(
        **base,
        local_authority_business_id=record.local_authority_business_id,
        rating_key=record.rating_key,
        hygiene_score=record.hygiene_score,
        structural_score=record.structural_score,
        confidence_in_management_score=record.confidence_in_management_score,
        longitude=record.longitude,
        latitude=record.latitude,
    )
