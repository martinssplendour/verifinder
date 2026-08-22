from __future__ import annotations

from sqlalchemy import JSON, Boolean, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class StudentSponsorRecord(Base):
    __tablename__ = "student_sponsor_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dataset_version_id: Mapped[str] = mapped_column(ForeignKey("dataset_versions.id"), index=True)
    source_record_key: Mapped[str] = mapped_column(String(40))
    organisation_name: Mapped[str] = mapped_column(String(400))
    normalised_name: Mapped[str] = mapped_column(String(400))
    town_city: Mapped[str | None] = mapped_column(String(180))
    additional_locations: Mapped[str | None] = mapped_column(Text)
    sponsor_type: Mapped[str | None] = mapped_column(String(180))
    status: Mapped[str | None] = mapped_column(String(120))
    routes: Mapped[list] = mapped_column(JSON, default=list)
    immigration_compliance: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        Index("ix_student_sponsor_version_key", "dataset_version_id", "source_record_key", unique=True),
        Index("ix_student_sponsor_version_name", "dataset_version_id", "normalised_name"),
    )


class OfsProviderRecord(Base):
    __tablename__ = "ofs_provider_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dataset_version_id: Mapped[str] = mapped_column(ForeignKey("dataset_versions.id"), index=True)
    ukprn: Mapped[str] = mapped_column(String(12))
    legal_name: Mapped[str] = mapped_column(String(400))
    normalised_name: Mapped[str] = mapped_column(String(400))
    trading_names: Mapped[list] = mapped_column(JSON, default=list)
    normalised_aliases: Mapped[str] = mapped_column(Text)
    contact_address: Mapped[str | None] = mapped_column(Text)
    postcode: Mapped[str | None] = mapped_column(String(16))
    email: Mapped[str | None] = mapped_column(String(240))
    website: Mapped[str | None] = mapped_column(Text)
    charity_status: Mapped[str | None] = mapped_column(String(120))
    registration_category: Mapped[str | None] = mapped_column(String(160))
    fee_limits: Mapped[str | None] = mapped_column(String(160))
    tef_rating: Mapped[str | None] = mapped_column(Text)
    degree_awarding_powers: Mapped[str | None] = mapped_column(String(160))
    degree_awarding_powers_date: Mapped[str | None] = mapped_column(String(80))
    university_title: Mapped[bool | None] = mapped_column(Boolean)
    university_title_date: Mapped[str | None] = mapped_column(String(80))
    university_title_basis: Mapped[str | None] = mapped_column(Text)
    access_plan: Mapped[bool | None] = mapped_column(Boolean)
    access_plan_url: Mapped[str | None] = mapped_column(Text)
    specific_conditions: Mapped[list] = mapped_column(JSON, default=list)

    __table_args__ = (
        Index("ix_ofs_provider_version_ukprn", "dataset_version_id", "ukprn", unique=True),
        Index("ix_ofs_provider_version_name", "dataset_version_id", "normalised_name"),
    )
