from __future__ import annotations

from datetime import date

from sqlalchemy import JSON, Boolean, Date, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SchoolRecord(Base):
    __tablename__ = "school_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dataset_version_id: Mapped[str] = mapped_column(ForeignKey("dataset_versions.id"), index=True)
    urn: Mapped[str] = mapped_column(String(20), index=True)
    la_name: Mapped[str | None] = mapped_column(String(180))
    establishment_name: Mapped[str] = mapped_column(String(400))
    normalised_name: Mapped[str] = mapped_column(String(400), index=True)
    type_name: Mapped[str | None] = mapped_column(String(160))
    type_group_name: Mapped[str | None] = mapped_column(String(160))
    status_name: Mapped[str | None] = mapped_column(String(80), index=True)
    phase_name: Mapped[str | None] = mapped_column(String(80), index=True)
    statutory_low_age: Mapped[int | None] = mapped_column(Integer)
    statutory_high_age: Mapped[int | None] = mapped_column(Integer)
    gender_name: Mapped[str | None] = mapped_column(String(80))
    religious_character_name: Mapped[str | None] = mapped_column(String(160))
    school_capacity: Mapped[int | None] = mapped_column(Integer)
    number_of_pupils: Mapped[int | None] = mapped_column(Integer)
    ukprn: Mapped[str | None] = mapped_column(String(12))
    open_date: Mapped[date | None] = mapped_column(Date)
    close_date: Mapped[date | None] = mapped_column(Date)
    street: Mapped[str | None] = mapped_column(String(240))
    locality: Mapped[str | None] = mapped_column(String(180))
    town: Mapped[str | None] = mapped_column(String(180))
    county_name: Mapped[str | None] = mapped_column(String(180))
    postcode: Mapped[str | None] = mapped_column(String(16))
    normalised_postcode: Mapped[str | None] = mapped_column(String(16), index=True)
    website: Mapped[str | None] = mapped_column(Text)
    telephone: Mapped[str | None] = mapped_column(String(40))
    head_first_name: Mapped[str | None] = mapped_column(String(120))
    head_last_name: Mapped[str | None] = mapped_column(String(120))
    region_name: Mapped[str | None] = mapped_column(String(80))
    country_name: Mapped[str | None] = mapped_column(String(80))
    raw_record: Mapped[dict] = mapped_column(JSON)

    __table_args__ = (
        Index("ix_school_version_urn", "dataset_version_id", "urn", unique=True),
        Index("ix_school_version_normalised_name", "dataset_version_id", "normalised_name"),
        Index("ix_school_version_postcode", "dataset_version_id", "normalised_postcode"),
    )


class OfstedInspectionRecord(Base):
    __tablename__ = "ofsted_inspection_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dataset_version_id: Mapped[str] = mapped_column(ForeignKey("dataset_versions.id"), index=True)
    urn: Mapped[str] = mapped_column(String(20), index=True)
    school_name: Mapped[str | None] = mapped_column(String(400))
    ofsted_phase: Mapped[str | None] = mapped_column(String(80))
    local_authority: Mapped[str | None] = mapped_column(String(180))
    region: Mapped[str | None] = mapped_column(String(80))
    postcode: Mapped[str | None] = mapped_column(String(16))
    most_recent_category_of_concern: Mapped[str | None] = mapped_column(String(160))
    full_inspection_number: Mapped[str | None] = mapped_column(String(40))
    full_inspection_type: Mapped[str | None] = mapped_column(String(80))
    full_inspection_start_date: Mapped[date | None] = mapped_column(Date)
    full_inspection_publication_date: Mapped[date | None] = mapped_column(Date)
    safeguarding_standards: Mapped[str | None] = mapped_column(String(80))
    inclusion: Mapped[str | None] = mapped_column(String(80))
    curriculum_and_teaching: Mapped[str | None] = mapped_column(String(80))
    achievement: Mapped[str | None] = mapped_column(String(80))
    attendance_and_behaviour: Mapped[str | None] = mapped_column(String(80))
    personal_development_and_wellbeing: Mapped[str | None] = mapped_column(String(80))
    early_years: Mapped[str | None] = mapped_column(String(80))
    post_16_provision: Mapped[str | None] = mapped_column(String(80))
    leadership_and_governance: Mapped[str | None] = mapped_column(String(80))
    oeif_start_date: Mapped[date | None] = mapped_column(Date)
    oeif_publication_date: Mapped[date | None] = mapped_column(Date)
    oeif_overall_effectiveness: Mapped[str | None] = mapped_column(String(4))
    oeif_safeguarding_effective: Mapped[bool | None] = mapped_column(Boolean)
    ungraded_inspection_date: Mapped[date | None] = mapped_column(Date)
    ungraded_publication_date: Mapped[date | None] = mapped_column(Date)
    ungraded_overall_outcome: Mapped[str | None] = mapped_column(String(160))
    raw_record: Mapped[dict] = mapped_column(JSON)

    __table_args__ = (
        Index("ix_ofsted_version_urn", "dataset_version_id", "urn", unique=True),
    )
