from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_read_db
from app.schemas import PropertyDetail, PropertySearchResponse
from app.services.epc import EPCClient
from app.services.property_lookup import get_property, search_properties, similar_properties


router = APIRouter()
settings = get_settings()


def epc_client() -> EPCClient | None:
    return EPCClient(settings.epc_api_key) if settings.epc_api_key else None


@router.get("/properties/search", response_model=PropertySearchResponse)
async def property_search(
    q: str = Query(min_length=2, max_length=240),
    limit: int = Query(default=20, ge=1, le=40),
    session: Session = Depends(get_read_db),
):
    results, context = search_properties(session, q, limit)
    suggestions = [] if results or context is None else similar_properties(session, q)
    return PropertySearchResponse(
        query=q,
        results=results,
        total=len(results),
        dataset_version=context[1].version_identifier if context else None,
        message=None if context else "The HM Land Registry Price Paid snapshot has not been imported.",
        suggestions=suggestions,
    )


@router.get("/properties/{property_key}", response_model=PropertyDetail)
async def property_detail(property_key: str, session: Session = Depends(get_read_db)):
    result = await get_property(session, property_key, epc_client=epc_client())
    if result is None:
        raise HTTPException(status_code=404, detail="Property not found in the latest imported sales snapshot.")
    return result
