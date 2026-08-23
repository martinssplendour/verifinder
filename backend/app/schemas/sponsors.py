from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.common import SourceAttribution


class SponsorRecordView(BaseModel):
    id: str
    organisation_name: str
    town_city: str | None = None
    county: str | None = None
    rating: str | None = None
    routes: list[str] = Field(default_factory=list)
    source: SourceAttribution


class SponsorSearchResponse(BaseModel):
    query: str
    results: list[SponsorRecordView]
    total: int
    dataset_version: str | None = None
    message: str | None = None
    suggestions: list[SponsorRecordView] = Field(default_factory=list)
