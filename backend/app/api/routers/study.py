from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_read_db
from app.schemas import StudyProviderDetail, StudyProviderSearchResponse
from app.services.study_lookup import get_study_provider, search_study_providers


router = APIRouter()


@router.get("/study/search", response_model=StudyProviderSearchResponse)
async def study_provider_search(
    q: str = Query(min_length=2, max_length=200),
    limit: int = Query(default=10, ge=1, le=25),
    session: Session = Depends(get_read_db),
):
    results, student_context, ofs_context = search_study_providers(session, q, limit)
    return StudyProviderSearchResponse(
        query=q,
        results=results,
        total=len(results),
        message=None if student_context or ofs_context else "No study-provider register has been imported.",
    )


@router.get("/study/{record_type}/{record_id}", response_model=StudyProviderDetail)
async def study_provider_detail(record_type: str, record_id: int, session: Session = Depends(get_read_db)):
    record = get_study_provider(session, record_type, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Study-provider record not found in the latest snapshots.")
    return record
