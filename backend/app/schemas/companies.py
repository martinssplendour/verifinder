from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field

from app.schemas.common import DataMode, SourceAttribution, VerificationStatus


class CompanyProfile(BaseModel):
    company_number: str
    company_name: str
    company_status: str | None
    incorporation_date: date | None
    registered_office: str | None
    postcode: str | None
    sic_codes: list[str] = Field(default_factory=list)
    company_type: str | None = None
    accounts_next_due: date | None = None
    verified_status: VerificationStatus
    data_mode: DataMode
    company_source: SourceAttribution


class Officer(BaseModel):
    name: str
    role: str
    appointed_on: date | None = None
    resigned_on: date | None = None
