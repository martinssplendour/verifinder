from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, Enum, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.common import MatchStatus, uuid_string, utc_now


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    company_number: Mapped[str] = mapped_column(String(12), unique=True, index=True)
    company_name: Mapped[str] = mapped_column(String(240))
    normalised_name: Mapped[str] = mapped_column(String(240), index=True)
    company_status: Mapped[str | None] = mapped_column(String(80))
    incorporation_date: Mapped[date | None] = mapped_column(Date)
    registered_address: Mapped[dict | None] = mapped_column(JSON)
    postcode: Mapped[str | None] = mapped_column(String(12), index=True)
    sic_codes: Mapped[list | None] = mapped_column(JSON)
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class EntityMapping(Base):
    __tablename__ = "entity_mappings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    sponsor_record_id: Mapped[str] = mapped_column(ForeignKey("sponsor_records.id"), index=True)
    status: Mapped[MatchStatus] = mapped_column(Enum(MatchStatus, native_enum=False))
    confidence: Mapped[float] = mapped_column(Float)
    match_method: Mapped[str] = mapped_column(String(80))
    manually_reviewed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
