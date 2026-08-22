from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


VerificationStatus = Literal[
    "verified", "match_found", "possible_match", "no_match", "data_unavailable", "stale", "unknown"
]
DataMode = Literal["live", "unavailable"]


class SourceAttribution(BaseModel):
    id: str
    organisation: str
    dataset: str
    official_url: str
    retrieved_at: datetime | None = None
    published_at: datetime | None = None
    version: str | None = None
    health: str = "unknown"


class SearchResult(BaseModel):
    company_number: str
    company_name: str
    status: str | None = None
    location: str | None = None
    company_type: str | None = None
    data_mode: DataMode


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]
    total: int
    data_mode: DataMode
    message: str | None = None


class ChangeItem(BaseModel):
    id: str
    change_type: str
    title: str
    detected_at: datetime
    source: SourceAttribution


class SourceRegistryItem(BaseModel):
    id: str
    organisation: str
    name: str
    official_url: str
    source_type: str
    refresh_frequency: str
    health: str
    last_successful_retrieval: datetime | None = None
    integration_status: Literal["connected", "configured", "not_configured"]
