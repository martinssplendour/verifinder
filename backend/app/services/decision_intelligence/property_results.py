from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import PropertySaleRecord
from app.schemas import AskInterpretation, AskResult, SourceAttribution
from app.services.dataset_utils import normalise_postcode
from app.services.property_lookup import latest_property_context, search_properties

from .interpretation import POSTCODE_RE
from .shared import _fact, _source


def _property_results(session: Session, query: AskInterpretation) -> tuple[list[AskResult], list[str]]:
    context = latest_property_context(session)
    if not context:
        return [], ["The 2025–2026 Price Paid snapshot has not been imported."]
    source, version = context
    term = query.location or query.subject or ""
    if POSTCODE_RE.fullmatch(term.strip()):
        records, _ = search_properties(session, term, query.limit)
        return [
            AskResult(
                rank=index,
                id=row.property_key,
                result_type="property_sale",
                title=row.address,
                subtitle=row.postcode,
                href=f"/property/{row.property_key}",
                facts=[_fact("Latest recorded price", f"£{row.latest_price:,.0f}"), _fact("Transfer date", row.latest_transfer_date.isoformat())],
                why_it_matches=[f"Recorded sale postcode matches {term.upper()}"],
                source=row.source,
            )
            for index, row in enumerate(records, start=1)
        ], ["Property coverage is deliberately limited to imported 2025–2026 Price Paid records for England and Wales."]
    rows = list(
        session.scalars(
            select(PropertySaleRecord)
            .where(
                PropertySaleRecord.dataset_version_id == version.id,
                PropertySaleRecord.town_city == term.upper(),
            )
            .order_by(PropertySaleRecord.transfer_date.desc())
            .limit(query.limit * 8)
        )
    )
    unique: dict[str, PropertySaleRecord] = {}
    for row in rows:
        unique.setdefault(row.property_key, row)
    attribution = _source((source, version))
    return [
        AskResult(
            rank=index,
            id=row.property_key,
            result_type="property_sale",
            title=row.full_address,
            subtitle=row.postcode,
            href=f"/property/{row.property_key}",
            facts=[_fact("Recorded price", f"£{row.price:,.0f}"), _fact("Transfer date", row.transfer_date.isoformat())],
            why_it_matches=[f"Recorded sale location matches {term}"],
            source=attribution,
        )
        for index, row in enumerate(list(unique.values())[: query.limit], start=1)
    ], ["Results are recent recorded sales, not current listings, valuations, or a recommendation to buy.", "Coverage is limited to the imported 2025–2026 snapshot."]


def _market_candidates(session: Session, location: str, budget: int | None) -> tuple[list[dict], SourceAttribution | None]:
    context = latest_property_context(session)
    if not context:
        return [], None
    source, version = context
    compact = normalise_postcode(location)
    postcode = bool(POSTCODE_RE.fullmatch(location.strip()))
    outward = func.substr(PropertySaleRecord.normalised_postcode, 1, func.length(PropertySaleRecord.normalised_postcode) - 3)
    conditions = [PropertySaleRecord.dataset_version_id == version.id, PropertySaleRecord.normalised_postcode.is_not(None)]
    if postcode:
        conditions.append(PropertySaleRecord.normalised_postcode == compact)
    else:
        conditions.append(PropertySaleRecord.town_city == location.upper())
    rows = session.execute(
        select(
            outward.label("outward"),
            func.count(PropertySaleRecord.id).label("sales"),
            func.avg(PropertySaleRecord.price).label("average"),
            func.min(PropertySaleRecord.price).label("minimum"),
            func.max(PropertySaleRecord.price).label("maximum"),
            func.max(PropertySaleRecord.transfer_date).label("latest"),
            func.max(PropertySaleRecord.postcode).label("representative_postcode"),
        )
        .where(*conditions)
        .group_by(outward)
        .order_by(func.count(PropertySaleRecord.id).desc())
        .limit(12)
    ).all()
    candidates = [
        {
            "outward": row.outward,
            "sales": int(row.sales),
            "average": round(float(row.average)),
            "minimum": int(row.minimum),
            "maximum": int(row.maximum),
            "latest": row.latest,
            "representative_postcode": row.representative_postcode,
        }
        for row in rows
        if row.outward
    ]
    if budget:
        candidates.sort(key=lambda item: (abs(item["average"] - budget), -item["sales"]))
    return candidates, _source((source, version))
