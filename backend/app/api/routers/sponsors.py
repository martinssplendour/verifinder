from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_read_db
from app.schemas import SponsorRecordView, SponsorSearchResponse
from app.services.sponsor_lookup import get_sponsor_record, search_sponsor_records, suggest_sponsor_records


router = APIRouter()


@router.get("/sponsors/search", response_model=SponsorSearchResponse)
async def sponsor_search(
    q: str = Query(min_length=2, max_length=160),
    limit: int = Query(default=8, ge=1, le=20),
    session: Session = Depends(get_read_db),
):
    results, context = search_sponsor_records(session, q, limit)
    return SponsorSearchResponse(
        query=q,
        results=results,
        total=len(results),
        dataset_version=context.version.version_identifier if context else None,
        message=None if context else "The sponsor register has not been imported.",
    )


@router.get("/sponsors/suggestions", response_model=SponsorSearchResponse)
async def sponsor_suggestions(
    q: str = Query(min_length=2, max_length=160),
    limit: int = Query(default=4, ge=1, le=8),
    session: Session = Depends(get_read_db),
):
    results, context = suggest_sponsor_records(session, q, limit)
    return SponsorSearchResponse(
        query=q,
        results=results,
        total=len(results),
        dataset_version=context.version.version_identifier if context else None,
        message=None if context else "The sponsor register has not been imported.",
    )


@router.get("/sponsors/{record_id}", response_model=SponsorRecordView)
async def sponsor_detail(record_id: str, session: Session = Depends(get_read_db)):
    record = get_sponsor_record(session, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Sponsor record not found in the latest dataset version.")
    return record
