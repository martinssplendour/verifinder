from __future__ import annotations

import re
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
from app.services.dataset_utils import normalise_postcode
from app.services.epc import DOCS_URL as EPC_URL, EPCClient
from app.services.normalization import normalise_name
from app.services.property_loader import SOURCE_ID


POSTCODE_PATTERN = re.compile(r"^[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}$", re.IGNORECASE)


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
    if POSTCODE_PATTERN.fullmatch(query.strip()):
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
