from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_read_db
from app.schemas import AreaCheckResponse
from app.services.area_lookup import get_area_check, latest_postcode_context


router = APIRouter()


@router.get("/areas/check", response_model=AreaCheckResponse)
async def area_check(
    postcode: str = Query(min_length=5, max_length=10),
    session: Session = Depends(get_read_db),
):
    result = await get_area_check(session, postcode)
    if result is None:
        if latest_postcode_context(session) is None:
            raise HTTPException(status_code=503, detail="The Code-Point Open postcode dataset has not been imported.")
        raise HTTPException(status_code=404, detail="Postcode not found in the current Great Britain postcode snapshot.")
    return result
