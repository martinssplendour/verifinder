from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field

from app.schemas.common import SourceAttribution


class FoodEstablishmentSearchResult(BaseModel):
    id: str
    fhrs_id: str
    business_name: str
    business_type: str | None = None
    address: str | None = None
    postcode: str | None = None
    rating_value: str | None = None
    rating_date: date | None = None
    local_authority_name: str | None = None
    scheme_type: str | None = None
    new_rating_pending: bool | None = None
    source: SourceAttribution


class FoodSearchResponse(BaseModel):
    query: str
    results: list[FoodEstablishmentSearchResult]
    total: int
    dataset_version: str | None = None
    message: str | None = None


class FoodEstablishmentView(FoodEstablishmentSearchResult):
    local_authority_business_id: str | None = None
    rating_key: str | None = None
    hygiene_score: int | None = None
    structural_score: int | None = None
    confidence_in_management_score: int | None = None
    longitude: float | None = None
    latitude: float | None = None
