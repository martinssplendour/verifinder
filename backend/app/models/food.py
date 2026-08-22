from __future__ import annotations

from datetime import date

from sqlalchemy import JSON, Boolean, Date, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.common import uuid_string


class FoodEstablishmentRecord(Base):
    __tablename__ = "food_establishment_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    dataset_version_id: Mapped[str] = mapped_column(ForeignKey("dataset_versions.id"), index=True)
    fhrs_id: Mapped[str] = mapped_column(String(40), index=True)
    local_authority_business_id: Mapped[str | None] = mapped_column(String(120))
    business_name: Mapped[str] = mapped_column(String(500))
    normalised_name: Mapped[str] = mapped_column(String(500), index=True)
    business_type: Mapped[str | None] = mapped_column(String(180), index=True)
    address: Mapped[str | None] = mapped_column(Text)
    postcode: Mapped[str | None] = mapped_column(String(16), index=True)
    normalised_postcode: Mapped[str | None] = mapped_column(String(16), index=True)
    rating_value: Mapped[str | None] = mapped_column(String(80), index=True)
    rating_key: Mapped[str | None] = mapped_column(String(100))
    rating_date: Mapped[date | None] = mapped_column(Date, index=True)
    local_authority_code: Mapped[str | None] = mapped_column(String(30))
    local_authority_name: Mapped[str | None] = mapped_column(String(180), index=True)
    scheme_type: Mapped[str | None] = mapped_column(String(30))
    new_rating_pending: Mapped[bool | None] = mapped_column(Boolean)
    hygiene_score: Mapped[int | None] = mapped_column(Integer)
    structural_score: Mapped[int | None] = mapped_column(Integer)
    confidence_in_management_score: Mapped[int | None] = mapped_column(Integer)
    longitude: Mapped[float | None] = mapped_column(Float)
    latitude: Mapped[float | None] = mapped_column(Float)
    raw_record: Mapped[dict] = mapped_column(JSON)

    __table_args__ = (
        Index("ix_food_version_fhrs", "dataset_version_id", "fhrs_id", unique=True),
        Index("ix_food_version_normalised_name", "dataset_version_id", "normalised_name"),
        Index("ix_food_version_normalised_postcode", "dataset_version_id", "normalised_postcode"),
    )
