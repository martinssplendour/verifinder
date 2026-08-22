from __future__ import annotations

from sqlalchemy import JSON, Boolean, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.common import uuid_string


class SponsorRecord(Base):
    __tablename__ = "sponsor_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    dataset_version_id: Mapped[str] = mapped_column(ForeignKey("dataset_versions.id"), index=True)
    source_record_key: Mapped[str] = mapped_column(String(64), index=True)
    organisation_name: Mapped[str] = mapped_column(String(300))
    normalised_name: Mapped[str] = mapped_column(String(300), index=True)
    town_city: Mapped[str | None] = mapped_column(String(180), index=True)
    county: Mapped[str | None] = mapped_column(String(180))
    sponsor_rating: Mapped[str | None] = mapped_column(String(30))
    routes: Mapped[list] = mapped_column(JSON, default=list)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    raw_record: Mapped[list | dict] = mapped_column(JSON)

    __table_args__ = (
        Index("ix_sponsor_version_record", "dataset_version_id", "source_record_key", unique=True),
    )
