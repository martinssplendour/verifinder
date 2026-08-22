from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_read_db
from app.schemas import FoodEstablishmentView, FoodSearchResponse
from app.services.food_lookup import get_food_establishment, search_food_establishments


router = APIRouter()


@router.get("/food/search", response_model=FoodSearchResponse)
async def food_search(
    q: str = Query(min_length=2, max_length=200),
    limit: int = Query(default=10, ge=1, le=25),
    session: Session = Depends(get_read_db),
):
    results, context = search_food_establishments(session, q, limit)
    return FoodSearchResponse(
        query=q,
        results=results,
        total=len(results),
        dataset_version=context[1].version_identifier if context else None,
        message=None if context else "The Food Standards Agency ratings dataset has not been imported.",
    )


@router.get("/food/{record_id}", response_model=FoodEstablishmentView)
async def food_detail(record_id: str, session: Session = Depends(get_read_db)):
    record = get_food_establishment(session, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Food establishment not found in the latest ratings snapshot.")
    return record
