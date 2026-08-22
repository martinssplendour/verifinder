from __future__ import annotations

from datetime import date

from sqlalchemy import JSON, Boolean, Date, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.common import uuid_string


class AwardingOrganisationRecord(Base):
    __tablename__ = "awarding_organisation_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    dataset_version_id: Mapped[str] = mapped_column(ForeignKey("dataset_versions.id"), index=True)
    recognition_number: Mapped[str] = mapped_column(String(30), index=True)
    name: Mapped[str] = mapped_column(String(300))
    normalised_name: Mapped[str] = mapped_column(String(300), index=True)
    legal_name: Mapped[str | None] = mapped_column(String(300))
    acronym: Mapped[str | None] = mapped_column(String(80))
    website: Mapped[str | None] = mapped_column(Text)
    postcode: Mapped[str | None] = mapped_column(String(16), index=True)
    ofqual_status: Mapped[str | None] = mapped_column(String(80))
    ofqual_recognised_from: Mapped[date | None] = mapped_column(Date)
    ofqual_recognised_to: Mapped[date | None] = mapped_column(Date)
    ccea_status: Mapped[str | None] = mapped_column(String(80))
    raw_record: Mapped[dict] = mapped_column(JSON)

    __table_args__ = (
        Index("ix_awarding_org_version_number", "dataset_version_id", "recognition_number", unique=True),
    )


class QualificationRecord(Base):
    __tablename__ = "qualification_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    dataset_version_id: Mapped[str] = mapped_column(ForeignKey("dataset_versions.id"), index=True)
    qualification_number: Mapped[str] = mapped_column(String(40), index=True)
    normalised_number: Mapped[str] = mapped_column(String(40), index=True)
    title: Mapped[str] = mapped_column(String(600))
    normalised_title: Mapped[str] = mapped_column(String(600), index=True)
    awarding_organisation_number: Mapped[str] = mapped_column(String(30), index=True)
    awarding_organisation_name: Mapped[str] = mapped_column(String(300), index=True)
    awarding_organisation_acronym: Mapped[str | None] = mapped_column(String(80))
    level: Mapped[str | None] = mapped_column(String(100), index=True)
    sub_level: Mapped[str | None] = mapped_column(String(100))
    qualification_type: Mapped[str | None] = mapped_column(String(160), index=True)
    sector_subject_area: Mapped[str | None] = mapped_column(String(240))
    status: Mapped[str | None] = mapped_column(String(100), index=True)
    regulation_start_date: Mapped[date | None] = mapped_column(Date)
    operational_start_date: Mapped[date | None] = mapped_column(Date)
    operational_end_date: Mapped[date | None] = mapped_column(Date)
    certification_end_date: Mapped[date | None] = mapped_column(Date)
    total_credits: Mapped[float | None] = mapped_column(Float)
    total_qualification_time: Mapped[int | None] = mapped_column(Integer)
    guided_learning_hours: Mapped[int | None] = mapped_column(Integer)
    offered_in_england: Mapped[bool | None] = mapped_column(Boolean)
    offered_in_northern_ireland: Mapped[bool | None] = mapped_column(Boolean)
    grading_type: Mapped[str | None] = mapped_column(String(160))
    assessment_methods: Mapped[str | None] = mapped_column(Text)
    specification_url: Mapped[str | None] = mapped_column(Text)
    raw_record: Mapped[dict] = mapped_column(JSON)

    __table_args__ = (
        Index("ix_qualification_version_number", "dataset_version_id", "qualification_number", unique=True),
        Index("ix_qualification_version_normalised_number", "dataset_version_id", "normalised_number"),
        Index("ix_qualification_version_normalised_title", "dataset_version_id", "normalised_title"),
        Index("ix_qualification_version_level", "dataset_version_id", "level"),
    )


class QualificationExpansionRecord(Base):
    __tablename__ = "qualification_expansion_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dataset_version_id: Mapped[str] = mapped_column(ForeignKey("dataset_versions.id"), index=True)
    source_record_key: Mapped[str] = mapped_column(String(80))
    regulator: Mapped[str] = mapped_column(String(120))
    jurisdiction: Mapped[str] = mapped_column(String(80))
    qualification_number: Mapped[str | None] = mapped_column(String(80))
    normalised_number: Mapped[str | None] = mapped_column(String(80))
    approval_number: Mapped[str | None] = mapped_column(String(80))
    title: Mapped[str] = mapped_column(String(700))
    normalised_title: Mapped[str] = mapped_column(String(700))
    awarding_organisation_name: Mapped[str | None] = mapped_column(String(400))
    normalised_organisation_name: Mapped[str | None] = mapped_column(String(400))
    level: Mapped[str | None] = mapped_column(String(120))
    qualification_type: Mapped[str | None] = mapped_column(String(180))
    status: Mapped[str | None] = mapped_column(String(120))
    languages: Mapped[list] = mapped_column(JSON, default=list)
    review_type: Mapped[str | None] = mapped_column(String(120))
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    certification_end_date: Mapped[date | None] = mapped_column(Date)
    eligible_public_funding: Mapped[bool | None] = mapped_column(Boolean)

    __table_args__ = (
        Index("ix_qualification_expansion_version_key", "dataset_version_id", "source_record_key", unique=True),
        Index("ix_qualification_expansion_version_number", "dataset_version_id", "normalised_number"),
        Index("ix_qualification_expansion_version_title", "dataset_version_id", "normalised_title"),
        Index("ix_qualification_expansion_version_org", "dataset_version_id", "normalised_organisation_name"),
    )


class QualificationUnitRecord(Base):
    __tablename__ = "qualification_unit_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dataset_version_id: Mapped[str] = mapped_column(ForeignKey("dataset_versions.id"), index=True)
    unit_key: Mapped[str] = mapped_column(String(100))
    unit_reference: Mapped[str | None] = mapped_column(String(100))
    title: Mapped[str] = mapped_column(String(700))
    normalised_title: Mapped[str] = mapped_column(String(700))
    level: Mapped[str | None] = mapped_column(String(120))
    credit_value: Mapped[float | None] = mapped_column(Float)
    guided_learning_hours: Mapped[int | None] = mapped_column(Integer)

    __table_args__ = (
        Index("ix_qualification_unit_version_key", "dataset_version_id", "unit_key", unique=True),
    )


class QualificationUnitMapping(Base):
    __tablename__ = "qualification_unit_mappings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dataset_version_id: Mapped[str] = mapped_column(ForeignKey("dataset_versions.id"), index=True)
    qualification_number: Mapped[str] = mapped_column(String(80))
    normalised_qualification_number: Mapped[str] = mapped_column(String(80))
    unit_key: Mapped[str] = mapped_column(String(100))

    __table_args__ = (
        Index(
            "ix_qualification_unit_mapping_version_pair",
            "dataset_version_id",
            "normalised_qualification_number",
            "unit_key",
            unique=True,
        ),
    )
