from __future__ import annotations

from sqlalchemy import ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PostcodeRecord(Base):
    __tablename__ = "postcode_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dataset_version_id: Mapped[str] = mapped_column(ForeignKey("dataset_versions.id"), index=True)
    postcode: Mapped[str] = mapped_column(String(10))
    normalised_postcode: Mapped[str] = mapped_column(String(10))
    postcode_area: Mapped[str] = mapped_column(String(4), index=True)
    positional_quality: Mapped[int | None] = mapped_column(Integer)
    easting: Mapped[int] = mapped_column(Integer)
    northing: Mapped[int] = mapped_column(Integer)
    country_code: Mapped[str | None] = mapped_column(String(12))
    admin_county_code: Mapped[str | None] = mapped_column(String(12))
    admin_district_code: Mapped[str | None] = mapped_column(String(12))
    admin_ward_code: Mapped[str | None] = mapped_column(String(12))

    __table_args__ = (
        Index("ix_postcode_version_postcode", "dataset_version_id", "normalised_postcode", unique=True),
    )
