from __future__ import annotations

import enum
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import JSON, Boolean, Date, DateTime, Enum, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def uuid_string() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SourceHealth(str, enum.Enum):
    HEALTHY = "healthy"
    STALE = "stale"
    UNAVAILABLE = "unavailable"
    INGESTION_FAILED = "ingestion_failed"
    SCHEMA_CHANGED = "schema_changed"


class RunStatus(str, enum.Enum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    UNCHANGED = "unchanged"


class MatchStatus(str, enum.Enum):
    CONFIRMED = "confirmed"
    LIKELY = "likely"
    POSSIBLE = "possible"
    UNMATCHED = "unmatched"
    REJECTED = "rejected"


class DataSource(Base):
    __tablename__ = "data_sources"

    id: Mapped[str] = mapped_column(String(60), primary_key=True)
    organisation: Mapped[str] = mapped_column(String(180))
    name: Mapped[str] = mapped_column(String(240))
    source_type: Mapped[str] = mapped_column(String(40))
    official_url: Mapped[str] = mapped_column(Text)
    data_url: Mapped[str | None] = mapped_column(Text)
    country: Mapped[str] = mapped_column(String(2), default="GB")
    refresh_frequency: Mapped[str | None] = mapped_column(String(80))
    health: Mapped[SourceHealth] = mapped_column(Enum(SourceHealth), default=SourceHealth.UNAVAILABLE)
    last_successful_retrieval: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    versions: Mapped[list[DatasetVersion]] = relationship(back_populates="source")


class DatasetVersion(Base):
    __tablename__ = "dataset_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    source_id: Mapped[str] = mapped_column(ForeignKey("data_sources.id"), index=True)
    version_identifier: Mapped[str] = mapped_column(String(180))
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    file_hash: Mapped[str] = mapped_column(String(64), unique=True)
    record_count: Mapped[int] = mapped_column(Integer, default=0)
    storage_location: Mapped[str] = mapped_column(Text)
    processing_status: Mapped[RunStatus] = mapped_column(Enum(RunStatus))

    source: Mapped[DataSource] = relationship(back_populates="versions")


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    source_id: Mapped[str] = mapped_column(ForeignKey("data_sources.id"), index=True)
    dataset_version_id: Mapped[str | None] = mapped_column(ForeignKey("dataset_versions.id"))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[RunStatus] = mapped_column(Enum(RunStatus))
    records_processed: Mapped[int] = mapped_column(Integer, default=0)
    records_added: Mapped[int] = mapped_column(Integer, default=0)
    records_removed: Mapped[int] = mapped_column(Integer, default=0)
    records_changed: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)


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


class EntityMapping(Base):
    __tablename__ = "entity_mappings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    sponsor_record_id: Mapped[str] = mapped_column(ForeignKey("sponsor_records.id"), index=True)
    status: Mapped[MatchStatus] = mapped_column(Enum(MatchStatus))
    confidence: Mapped[float] = mapped_column(Float)
    match_method: Mapped[str] = mapped_column(String(80))
    manually_reviewed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ChangeEvent(Base):
    __tablename__ = "change_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    source_id: Mapped[str] = mapped_column(ForeignKey("data_sources.id"), index=True)
    previous_dataset_version_id: Mapped[str | None] = mapped_column(ForeignKey("dataset_versions.id"))
    current_dataset_version_id: Mapped[str] = mapped_column(ForeignKey("dataset_versions.id"), index=True)
    source_record_key: Mapped[str] = mapped_column(String(64), index=True)
    change_type: Mapped[str] = mapped_column(String(50), index=True)
    previous_value: Mapped[dict | None] = mapped_column(JSON)
    new_value: Mapped[dict | None] = mapped_column(JSON)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
