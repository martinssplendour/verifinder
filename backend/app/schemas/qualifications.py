from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import SourceAttribution


class QualificationSearchResult(BaseModel):
    id: str
    qualification_number: str
    title: str
    awarding_organisation_name: str
    awarding_organisation_acronym: str | None = None
    level: str | None = None
    qualification_type: str | None = None
    status: str | None = None
    record_type: Literal["ofqual", "qiw"] = "ofqual"
    regulator: str = "Ofqual / CCEA Regulation"
    jurisdiction: str = "England and Northern Ireland"
    source: SourceAttribution


class QualificationSearchResponse(BaseModel):
    query: str
    results: list[QualificationSearchResult]
    total: int
    dataset_version: str | None = None
    message: str | None = None


class QualificationRecordView(QualificationSearchResult):
    sector_subject_area: str | None = None
    regulation_start_date: date | None = None
    operational_start_date: date | None = None
    operational_end_date: date | None = None
    certification_end_date: date | None = None
    total_credits: float | None = None
    total_qualification_time: int | None = None
    guided_learning_hours: int | None = None
    offered_in_england: bool | None = None
    offered_in_northern_ireland: bool | None = None
    grading_type: str | None = None
    assessment_methods: str | None = None
    specification_url: str | None = None
    approval_number: str | None = None
    languages: list[str] = Field(default_factory=list)
    review_type: str | None = None
    eligible_public_funding: bool | None = None
    unit_count: int = 0
    units: list[QualificationUnitView] = Field(default_factory=list)


class QualificationUnitView(BaseModel):
    unit_reference: str | None = None
    title: str
    level: str | None = None
    credit_value: float | None = None
    guided_learning_hours: int | None = None
