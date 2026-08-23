from fastapi import APIRouter, HTTPException, Query

from app.config import get_settings
from app.schemas import (
    CompanyProfile,
    Officer,
    SearchResponse,
    SourceAttribution,
)
from app.services.companies_house import CompaniesHouseClient, CompaniesHouseError


router = APIRouter()
settings = get_settings()
COMPANIES_HOUSE_UNAVAILABLE = "Companies House is not connected. Configure COMPANIES_HOUSE_API_KEY to enable legal-company records."


def companies_house_client() -> CompaniesHouseClient | None:
    return CompaniesHouseClient(settings.companies_house_api_key) if settings.companies_house_api_key else None


async def _company_profile(company_number: str) -> CompanyProfile:
    client = companies_house_client()
    if not client:
        raise HTTPException(status_code=503, detail=COMPANIES_HOUSE_UNAVAILABLE)
    try:
        base_profile = await client.profile(company_number)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="Company not found.") from error
    except CompaniesHouseError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    return base_profile


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
        results, suggestions = await client.search_with_suggestions(q, limit)
    except CompaniesHouseError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    return SearchResponse(
        query=q,
        results=results,
        total=len(results),
        data_mode="live",
        suggestions=suggestions,
    )


@router.get("/search/suggestions", response_model=SearchResponse)
async def search_suggestions(
    q: str = Query(min_length=2, max_length=160),
    limit: int = Query(default=4, ge=1, le=8),
):
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
        results = await client.suggestions(q, limit)
    except CompaniesHouseError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    return SearchResponse(query=q, results=results, total=len(results), data_mode="live")


@router.get("/companies/{company_number}", response_model=CompanyProfile)
async def company_profile(company_number: str):
    return await _company_profile(company_number)


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
async def company_sources(company_number: str):
    profile = await _company_profile(company_number)
    return [profile.company_source]
