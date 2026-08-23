from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_read_db
from app.schemas import SchoolDetail, SchoolSearchResponse
from app.services.school_lookup import get_school, search_schools, similar_schools


router = APIRouter()


@router.get("/schools/search", response_model=SchoolSearchResponse)
async def school_search(
    q: str = Query(min_length=2, max_length=200),
    limit: int = Query(default=10, ge=1, le=25),
    session: Session = Depends(get_read_db),
):
    results, context = search_schools(session, q, limit)
    suggestions = [] if results or context is None else similar_schools(session, q)
    return SchoolSearchResponse(
        query=q,
        results=results,
        total=len(results),
        dataset_version=context[1].version_identifier if context else None,
        message=None if context else "The GIAS establishment register has not been imported.",
        suggestions=suggestions,
    )


@router.get("/schools/{urn}", response_model=SchoolDetail)
async def school_detail(urn: str, session: Session = Depends(get_read_db)):
    record = get_school(session, urn)
    if record is None:
        raise HTTPException(status_code=404, detail="School not found in the latest imported GIAS snapshot.")
    return record
