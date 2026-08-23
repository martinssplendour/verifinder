from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_read_db
from app.schemas import QualificationRecordView, QualificationSearchResponse
from app.services.qualification_lookup import (
    get_qualification,
    latest_qualification_context,
    latest_welsh_qualification_context,
    search_qualifications,
    similar_qualifications,
)


router = APIRouter()


@router.get("/qualifications/search", response_model=QualificationSearchResponse)
async def qualification_search(
    q: str = Query(min_length=2, max_length=200),
    limit: int = Query(default=10, ge=1, le=25),
    session: Session = Depends(get_read_db),
):
    results, context = search_qualifications(session, q, limit)
    contexts = [
        item
        for item in (latest_qualification_context(session), latest_welsh_qualification_context(session))
        if item
    ]
    suggestions = [] if results or context is None else similar_qualifications(session, q)
    return QualificationSearchResponse(
        query=q,
        results=results,
        total=len(results),
        dataset_version=" · ".join(item[1].version_identifier for item in contexts) or None,
        message=None if context else "No qualification register has been imported.",
        suggestions=suggestions,
    )


@router.get("/qualifications/{record_id}", response_model=QualificationRecordView)
async def qualification_detail(record_id: str, session: Session = Depends(get_read_db)):
    record = get_qualification(session, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Qualification not found in the latest register snapshot.")
    return record
