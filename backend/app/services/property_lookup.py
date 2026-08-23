from __future__ import annotations

import statistics

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DataSource, DatasetVersion, PropertySaleRecord, RunStatus
from app.schemas import (
    EPCSummary,
    NearbySalesSummary,
    PlanningSummary,
    PropertyDetail,
    PropertySale,
    PropertySearchResult,
    SourceAttribution,
)
from app.services.area_sources import PLANNING_URL, PlanningDataClient
from app.services.dataset_utils import looks_like_postcode, normalise_postcode
from app.services.epc import DOCS_URL as EPC_URL, EPCClient
from app.services.normalization import normalise_name
from app.services.search_suggestions import (
    CANDIDATE_LIMIT,
    SUGGESTION_LIMIT,
    candidate_filter,
    rank_near_matches,
)
from app.services.property_loader import SOURCE_ID



def latest_property_context(session: Session) -> tuple[DataSource, DatasetVersion] | None:
    source = session.get(DataSource, SOURCE_ID)
    if source is None:
        return None
    version = session.scalar(
        select(DatasetVersion)
        .where(DatasetVersion.source_id == SOURCE_ID, DatasetVersion.processing_status == RunStatus.SUCCEEDED)
        .order_by(DatasetVersion.retrieved_at.desc())
        .limit(1)
    )
    return (source, version) if version else None


def _attribution(source: DataSource, version: DatasetVersion) -> SourceAttribution:
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


def search_properties(session: Session, query: str, limit: int = 20) -> tuple[list[PropertySearchResult], tuple[DataSource, DatasetVersion] | None]:
    context = latest_property_context(session)
    if context is None:
        return [], None
    source, version = context
    statement = select(PropertySaleRecord).where(PropertySaleRecord.dataset_version_id == version.id)
    if looks_like_postcode(query):
        statement = statement.where(PropertySaleRecord.normalised_postcode == normalise_postcode(query))
    else:
        normalised = normalise_name(query)
        if len(normalised) < 2:
            return [], context
        statement = statement.where(
            PropertySaleRecord.normalised_address >= normalised,
            PropertySaleRecord.normalised_address < f"{normalised}\uffff",
        )
    records = list(session.scalars(statement.order_by(PropertySaleRecord.transfer_date.desc()).limit(max(500, limit * 20))))
    grouped: dict[str, list[PropertySaleRecord]] = {}
    for record in records:
        grouped.setdefault(record.property_key, []).append(record)
    attribution = _attribution(source, version)
    results = [
        PropertySearchResult(
            property_key=key,
            address=items[0].full_address,
            postcode=items[0].postcode,
            latest_price=items[0].price,
            latest_transfer_date=items[0].transfer_date,
            property_type=items[0].property_type,
            transaction_count=len(items),
            source=attribution,
        )
        for key, items in list(grouped.items())[:limit]
    ]
    return results, context


def similar_properties(session: Session, query: str, limit: int = SUGGESTION_LIMIT) -> list[PropertySearchResult]:
    """Nearby recorded sales to offer when the searched address or postcode has none.

    A postcode with no sale in the snapshot falls back to its wider sector, which
    is the honest answer to "is there anything around here?" without implying the
    searched address itself was found.
    """
    context = latest_property_context(session)
    if context is None:
        return []
    source, version = context
    is_postcode = looks_like_postcode(query)
    target = (normalise_postcode(query) or "") if is_postcode else normalise_name(query)
    column = PropertySaleRecord.normalised_postcode if is_postcode else PropertySaleRecord.normalised_address
    condition = candidate_filter(column, target)
    if condition is None:
        return []
    candidates = list(
        session.scalars(
            select(PropertySaleRecord)
            .where(PropertySaleRecord.dataset_version_id == version.id, condition)
            .order_by(PropertySaleRecord.transfer_date.desc())
            .limit(CANDIDATE_LIMIT)
        )
    )
    grouped: dict[str, list[PropertySaleRecord]] = {}
    for record in candidates:
        grouped.setdefault(record.property_key, []).append(record)
    key = (
        (lambda items: items[0].normalised_postcode)
        if is_postcode
        else (lambda items: items[0].normalised_address)
    )
    ranked = rank_near_matches(list(grouped.values()), target, key, limit)
    attribution = _attribution(source, version)
    return [
        PropertySearchResult(
            property_key=items[0].property_key,
            address=items[0].full_address,
            postcode=items[0].postcode,
            latest_price=items[0].price,
            latest_transfer_date=items[0].transfer_date,
            property_type=items[0].property_type,
            transaction_count=len(items),
            source=attribution,
        )
        for items in ranked
    ]


async def get_property(
    session: Session,
    property_key: str,
    planning_client: PlanningDataClient | None = None,
    epc_client: EPCClient | None = None,
) -> PropertyDetail | None:
    context = latest_property_context(session)
    if context is None:
        return None
    source, version = context
    records = list(
        session.scalars(
            select(PropertySaleRecord)
            .where(
                PropertySaleRecord.dataset_version_id == version.id,
                PropertySaleRecord.property_key == property_key,
            )
            .order_by(PropertySaleRecord.transfer_date.desc())
        )
    )
    if not records:
        return None
    latest = records[0]
    nearby_records = list(
        session.scalars(
            select(PropertySaleRecord).where(
                PropertySaleRecord.dataset_version_id == version.id,
                PropertySaleRecord.normalised_postcode == latest.normalised_postcode,
            )
        )
    ) if latest.normalised_postcode else []
    prices = [record.price for record in nearby_records]
    nearby = NearbySalesSummary(
        postcode=latest.postcode or "",
        count=len(prices),
        median_price=round(statistics.median(prices)) if prices else None,
        minimum_price=min(prices) if prices else None,
        maximum_price=max(prices) if prices else None,
    ) if latest.postcode else None
    try:
        planning = await (planning_client or PlanningDataClient()).summary(latest.postcode or "")
    except Exception:
        planning = PlanningSummary(
            status="unavailable", source_url=PLANNING_URL, message="Planning Data is temporarily unavailable."
        )
    if epc_client is None:
        epc = EPCSummary(
            status="unavailable",
            source_url=EPC_URL,
            message="EPC register is not connected. Configure EPC_API_KEY to enable Energy Performance Certificate data.",
        )
    else:
        try:
            epc = await epc_client.search(latest.postcode or "")
        except Exception:
            epc = EPCSummary(status="unavailable", source_url=EPC_URL, message="EPC register is temporarily unavailable.")
    epc_limitation = (
        "Energy Performance Certificate data is not connected."
        if epc_client is None
        else "Energy Performance Certificate data is matched by postcode; a returned certificate may belong to a nearby property rather than this exact address."
    )
    return PropertyDetail(
        property_key=property_key,
        address=latest.full_address,
        postcode=latest.postcode,
        property_type=latest.property_type,
        town_city=latest.town_city,
        district=latest.district,
        county=latest.county,
        sales=[
            PropertySale(
                transaction_id=record.transaction_id,
                price=record.price,
                transfer_date=record.transfer_date,
                property_type=record.property_type,
                new_build=record.new_build,
                tenure=record.tenure,
                ppd_category=record.ppd_category,
            )
            for record in records
        ],
        nearby_sales=nearby,
        planning=planning,
        epc=epc,
        source=_attribution(source, version),
        limitations=[
            "Sale history is limited to the imported 2025–2026 Price Paid snapshot for England and Wales.",
            "A missing sale does not mean a property has never sold; some transactions are excluded or not yet registered.",
            "Planning context is matched at postcode level, not to a title number or exact UPRN.",
            epc_limitation,
        ],
    )
