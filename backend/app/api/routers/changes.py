from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_read_db
from app.models import ChangeEvent
from app.schemas import ChangeItem, SourceAttribution
from app.services.sponsor_lookup import latest_sponsor_context, source_attribution


router = APIRouter()


def _change_item(event: ChangeEvent, source: SourceAttribution) -> ChangeItem:
    payload = event.new_value or event.previous_value or {}
    organisation = payload.get("organisation_name", "Sponsor organisation")
    titles = {
        "sponsor_added": f"{organisation} was added to the sponsor register",
        "sponsor_removed": f"{organisation} was removed from the sponsor register",
        "route_changed": f"Sponsorship routes changed for {organisation}",
        "rating_changed": f"Sponsor rating changed for {organisation}",
        "organisation_changed": f"Sponsor information changed for {organisation}",
    }
    return ChangeItem(
        id=event.id,
        change_type=event.change_type,
        title=titles.get(event.change_type, f"Sponsor information changed for {organisation}"),
        detected_at=event.detected_at,
        source=source,
    )


@router.get("/changes", response_model=list[ChangeItem])
async def changes(session: Session = Depends(get_read_db)):
    context = latest_sponsor_context(session)
    if not context:
        return []
    events = list(session.scalars(select(ChangeEvent).order_by(ChangeEvent.detected_at.desc()).limit(100)))
    attribution = source_attribution(context)
    return [_change_item(event, attribution) for event in events]
