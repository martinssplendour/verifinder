from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import SourceAttribution


class StudyProviderSearchResult(BaseModel):
    id: str
    record_type: Literal["student_sponsor", "ofs"]
    name: str
    town_city: str | None = None
    provider_type: str | None = None
    status: str | None = None
    routes: list[str] = Field(default_factory=list)
    ukprn: str | None = None
    source: SourceAttribution


class StudyProviderSearchResponse(BaseModel):
    query: str
    results: list[StudyProviderSearchResult]
    total: int
    message: str | None = None


class StudyProviderDetail(BaseModel):
    id: str
    record_type: Literal["student_sponsor", "ofs"]
    name: str
    town_city: str | None = None
    provider_type: str | None = None
    status: str | None = None
    routes: list[str] = Field(default_factory=list)
    additional_locations: str | None = None
    immigration_compliance: str | None = None
    ukprn: str | None = None
    trading_names: list[str] = Field(default_factory=list)
    contact_address: str | None = None
    postcode: str | None = None
    email: str | None = None
    website: str | None = None
    charity_status: str | None = None
    registration_category: str | None = None
    fee_limits: str | None = None
    tef_rating: str | None = None
    degree_awarding_powers: str | None = None
    degree_awarding_powers_date: str | None = None
    university_title: bool | None = None
    university_title_date: str | None = None
    university_title_basis: str | None = None
    access_plan: bool | None = None
    access_plan_url: str | None = None
    specific_conditions: list[str] = Field(default_factory=list)
    matched_record: StudyProviderSearchResult | None = None
    source: SourceAttribution
    limitations: list[str] = Field(default_factory=list)
