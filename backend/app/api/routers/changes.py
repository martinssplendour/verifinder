from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.routers.companies import _change_item
from app.database import get_read_db
from app.models import ChangeEvent
from app.schemas import ChangeItem
from app.services.sponsor_lookup import latest_sponsor_context, source_attribution


router = APIRouter()


@router.get("/changes", response_model=list[ChangeItem])
async def changes(session: Session = Depends(get_read_db)):
    context = latest_sponsor_context(session)
    if not context:
        return []
    events = list(session.scalars(select(ChangeEvent).order_by(ChangeEvent.detected_at.desc()).limit(100)))
    attribution = source_attribution(context)
    return [_change_item(event, attribution) for event in events]
