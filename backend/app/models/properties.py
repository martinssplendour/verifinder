from __future__ import annotations

from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PropertySaleRecord(Base):
    __tablename__ = "property_sale_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dataset_version_id: Mapped[str] = mapped_column(ForeignKey("dataset_versions.id"), index=True)
    transaction_id: Mapped[str] = mapped_column(String(50))
    price: Mapped[int] = mapped_column(Integer)
    transfer_date: Mapped[date] = mapped_column(Date, index=True)
    postcode: Mapped[str | None] = mapped_column(String(10))
    normalised_postcode: Mapped[str | None] = mapped_column(String(10))
    property_type: Mapped[str | None] = mapped_column(String(1))
    new_build: Mapped[bool | None] = mapped_column(Boolean)
    tenure: Mapped[str | None] = mapped_column(String(1))
    paon: Mapped[str | None] = mapped_column(String(120))
    saon: Mapped[str | None] = mapped_column(String(120))
    street: Mapped[str | None] = mapped_column(String(240))
    locality: Mapped[str | None] = mapped_column(String(180))
    town_city: Mapped[str | None] = mapped_column(String(180))
    district: Mapped[str | None] = mapped_column(String(180))
    county: Mapped[str | None] = mapped_column(String(180))
    full_address: Mapped[str] = mapped_column(Text)
    normalised_address: Mapped[str] = mapped_column(Text)
    property_key: Mapped[str] = mapped_column(String(32))
    ppd_category: Mapped[str | None] = mapped_column(String(1))
    record_status: Mapped[str | None] = mapped_column(String(1))

    __table_args__ = (
        Index("ix_property_version_transaction", "dataset_version_id", "transaction_id", unique=True),
        Index("ix_property_version_postcode", "dataset_version_id", "normalised_postcode"),
        Index("ix_property_version_address", "dataset_version_id", "normalised_address"),
        Index("ix_property_version_key", "dataset_version_id", "property_key"),
        Index("ix_property_version_town", "dataset_version_id", "town_city"),
        Index("ix_property_version_district", "dataset_version_id", "district"),
    )
