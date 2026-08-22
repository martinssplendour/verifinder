from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.schemas.intelligence import DecisionPlanResponse


class SavedReportCreate(BaseModel):
    plan: DecisionPlanResponse


class SavedReportView(BaseModel):
    id: str
    source_report_id: str
    report_type: str
    title: str
    mime_type: str
    size_bytes: int
    provenance_count: int
    created_at: datetime


class SavedReportReady(BaseModel):
    report: SavedReportView
    download_url: str
    expires_at: datetime


class SignedDownloadResponse(BaseModel):
    url: str
    expires_at: datetime
