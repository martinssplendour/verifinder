from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class WatchlistEntryCreate(BaseModel):
    entity_type: Literal["company", "area", "school", "food", "qualification", "property", "sponsor"]
    entity_id: str = Field(min_length=1, max_length=120)
    label: str | None = Field(default=None, max_length=300)


class WatchlistEntryView(BaseModel):
    id: int
    entity_type: str
    entity_id: str
    label: str | None
    notifications_enabled: bool
    created_at: datetime


class WatchlistEntryUpdate(BaseModel):
    notifications_enabled: bool


class WatchlistAlertView(BaseModel):
    id: int
    entity_type: str
    entity_id: str
    summary: str
    detail: dict | None
    email_status: str
    created_at: datetime
