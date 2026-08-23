from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import FoodEstablishmentRecord
from app.schemas import AskInterpretation, AskResult
from app.services.food_lookup import latest_food_context

from .shared import _fact, _source


def _food_results(session: Session, query: AskInterpretation) -> tuple[list[AskResult], list[str]]:
    context = latest_food_context(session)
    if not context:
        return [], ["The Food Standards Agency snapshot has not been imported."]
    _, version = context
    conditions = [FoodEstablishmentRecord.dataset_version_id == version.id]
    term = query.location or query.subject
    if term:
        value = term.lower()
        conditions.append(
            or_(
                func.lower(FoodEstablishmentRecord.business_name).contains(value),
                func.lower(FoodEstablishmentRecord.address).contains(value),
                func.lower(FoodEstablishmentRecord.local_authority_name).contains(value),
                func.lower(FoodEstablishmentRecord.postcode).contains(value),
            )
        )
    rows = list(
        session.scalars(
            select(FoodEstablishmentRecord)
            .where(*conditions)
            .order_by(FoodEstablishmentRecord.rating_value.desc(), FoodEstablishmentRecord.rating_date.desc())
            .limit(query.limit)
        )
    )
    source = _source(context)
    return [
        AskResult(
            rank=index,
            id=row.id,
            result_type="food_establishment",
            title=row.business_name,
            subtitle=row.business_type,
            href=f"/food/{row.id}",
            facts=[
                _fact("Food hygiene rating", row.rating_value or "Not stated"),
                _fact("Rating date", row.rating_date.isoformat() if row.rating_date else "Not stated"),
                _fact("Address", ", ".join(filter(None, (row.address, row.postcode))) or "Not stated"),
            ],
            why_it_matches=[f"Official record matches {term}" if term else "Current official food hygiene record"],
            source=source,
        )
        for index, row in enumerate(rows, start=1)
    ], ["Food hygiene ratings measure compliance at inspection; they are not reviews of taste, price, or service."]
