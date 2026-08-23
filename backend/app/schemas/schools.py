from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import SourceAttribution


class OfstedInspectionSummary(BaseModel):
    status: Literal["matched", "data_unavailable"]
    urn: str | None = None
    most_recent_category_of_concern: str | None = None
    full_inspection_type: str | None = None
    full_inspection_start_date: date | None = None
    full_inspection_publication_date: date | None = None
    safeguarding_standards: str | None = None
    inclusion: str | None = None
    curriculum_and_teaching: str | None = None
    achievement: str | None = None
    attendance_and_behaviour: str | None = None
    personal_development_and_wellbeing: str | None = None
    early_years: str | None = None
    post_16_provision: str | None = None
    leadership_and_governance: str | None = None
    oeif_start_date: date | None = None
    oeif_publication_date: date | None = None
    oeif_overall_effectiveness: str | None = None
    oeif_safeguarding_effective: bool | None = None
    ungraded_inspection_date: date | None = None
    ungraded_publication_date: date | None = None
    ungraded_overall_outcome: str | None = None
    source: SourceAttribution | None = None
    message: str | None = None


class SchoolSearchResult(BaseModel):
    urn: str
    establishment_name: str
    la_name: str | None = None
    type_name: str | None = None
    phase_name: str | None = None
    status_name: str | None = None
    postcode: str | None = None
    town: str | None = None
    source: SourceAttribution


class SchoolSearchResponse(BaseModel):
    query: str
    results: list[SchoolSearchResult]
    total: int
    dataset_version: str | None = None
    message: str | None = None
    suggestions: list[SchoolSearchResult] = Field(default_factory=list)


class SchoolDetail(BaseModel):
    urn: str
    establishment_name: str
    la_name: str | None = None
    type_name: str | None = None
    type_group_name: str | None = None
    status_name: str | None = None
    phase_name: str | None = None
    statutory_low_age: int | None = None
    statutory_high_age: int | None = None
    gender_name: str | None = None
    religious_character_name: str | None = None
    school_capacity: int | None = None
    number_of_pupils: int | None = None
    ukprn: str | None = None
    open_date: date | None = None
    close_date: date | None = None
    street: str | None = None
    locality: str | None = None
    town: str | None = None
    county_name: str | None = None
    postcode: str | None = None
    website: str | None = None
    telephone: str | None = None
    head_first_name: str | None = None
    head_last_name: str | None = None
    region_name: str | None = None
    country_name: str | None = None
    source: SourceAttribution
    ofsted: OfstedInspectionSummary
    limitations: list[str] = Field(default_factory=list)
