from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field

from app.schemas.common import DataMode, SourceAttribution


class PostcodePoint(BaseModel):
    postcode: str
    latitude: float
    longitude: float
    country_code: str | None = None
    admin_district_code: str | None = None
    admin_ward_code: str | None = None
    source: SourceAttribution


class CrimeMonth(BaseModel):
    month: str
    count: int


class CrimeCategoryCount(BaseModel):
    category: str
    count: int


class CrimeSummary(BaseModel):
    status: DataMode
    latest_month: str | None = None
    latest_total: int | None = None
    months: list[CrimeMonth] = Field(default_factory=list)
    categories: list[CrimeCategoryCount] = Field(default_factory=list)
    source_url: str
    message: str | None = None


class PlanningConstraint(BaseModel):
    dataset: str
    name: str
    reference: str | None = None
    start_date: date | None = None


class PlanningSummary(BaseModel):
    status: DataMode
    total: int | None = None
    constraints: list[PlanningConstraint] = Field(default_factory=list)
    source_url: str
    message: str | None = None


class EPCCertificate(BaseModel):
    certificate_number: str
    address: str
    postcode: str | None = None
    current_rating: str | None = None
    lodgement_date: str | None = None
    uprn: str | None = None


class EPCSummary(BaseModel):
    status: DataMode
    total: int | None = None
    certificates: list[EPCCertificate] = Field(default_factory=list)
    source_url: str
    message: str | None = None


class FloodWarning(BaseModel):
    severity: str
    severity_level: int
    description: str
    area: str | None = None
    time_raised: datetime | None = None
    time_message_changed: datetime | None = None


class FloodSummary(BaseModel):
    status: DataMode
    total: int | None = None
    warnings: list[FloodWarning] = Field(default_factory=list)
    radius_km: int = 10
    source_url: str
    message: str | None = None


class AreaCheckResponse(BaseModel):
    postcode: PostcodePoint
    crime: CrimeSummary
    planning: PlanningSummary
    flood: FloodSummary
    limitations: list[str] = Field(default_factory=list)
