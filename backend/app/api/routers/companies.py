from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_read_db
from app.models import ChangeEvent
from app.schemas import (
    ChangeItem,
    CompanyProfile,
    Officer,
    SearchResponse,
    SourceAttribution,
)
from app.services.companies_house import CompaniesHouseClient, CompaniesHouseError
from app.services.sponsor_lookup import (
    SponsorResolution,
    resolve_company_sponsorship,
    source_attribution,
)


router = APIRouter()
settings = get_settings()
COMPANIES_HOUSE_UNAVAILABLE = "Companies House is not connected. Configure COMPANIES_HOUSE_API_KEY to enable legal-company records."


def companies_house_client() -> CompaniesHouseClient | None:
    return CompaniesHouseClient(settings.companies_house_api_key) if settings.companies_house_api_key else None


async def _company_profile(company_number: str, session: Session) -> tuple[CompanyProfile, SponsorResolution]:
    client = companies_house_client()
    if not client:
        raise HTTPException(status_code=503, detail=COMPANIES_HOUSE_UNAVAILABLE)
    try:
        base_profile = await client.profile(company_number)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="Company not found.") from error
    except CompaniesHouseError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    resolution = resolve_company_sponsorship(
        session,
        company_name=base_profile.company_name,
        registered_office=base_profile.registered_office,
    )
    return base_profile.model_copy(update={"sponsorship": resolution.summary}), resolution


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


@router.get("/search", response_model=SearchResponse)
async def search(q: str = Query(min_length=2, max_length=160), limit: int = Query(default=8, ge=1, le=20)):
    client = companies_house_client()
    if not client:
        return SearchResponse(
            query=q,
            results=[],
            total=0,
            data_mode="unavailable",
            message=COMPANIES_HOUSE_UNAVAILABLE,
        )
    try:
        results = await client.search(q, limit)
    except CompaniesHouseError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    return SearchResponse(query=q, results=results, total=len(results), data_mode="live")


@router.get("/companies/{company_number}", response_model=CompanyProfile)
async def company_profile(company_number: str, session: Session = Depends(get_read_db)):
    profile, _ = await _company_profile(company_number, session)
    return profile


@router.get("/companies/{company_number}/sponsorship")
async def company_sponsorship(company_number: str, session: Session = Depends(get_read_db)):
    profile, _ = await _company_profile(company_number, session)
    return profile.sponsorship


@router.get("/companies/{company_number}/officers", response_model=list[Officer])
async def company_officers(company_number: str):
    client = companies_house_client()
    if not client:
        return []
    try:
        return await client.officers(company_number)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="Company not found.") from error
    except CompaniesHouseError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@router.get("/companies/{company_number}/sources", response_model=list[SourceAttribution])
async def company_sources(company_number: str, session: Session = Depends(get_read_db)):
    profile, _ = await _company_profile(company_number, session)
    sources = [profile.company_source]
    if profile.sponsorship.source:
        sources.append(profile.sponsorship.source)
    return sources


@router.get("/companies/{company_number}/changes", response_model=list[ChangeItem])
async def company_changes(company_number: str, session: Session = Depends(get_read_db)):
    _, resolution = await _company_profile(company_number, session)
    if not resolution.record or not resolution.context:
        return []
    events = list(
        session.scalars(
            select(ChangeEvent)
            .where(ChangeEvent.source_record_key == resolution.record.source_record_key)
            .order_by(ChangeEvent.detected_at.desc())
            .limit(50)
        )
    )
    attribution = source_attribution(resolution.context)
    return [_change_item(event, attribution) for event in events]
