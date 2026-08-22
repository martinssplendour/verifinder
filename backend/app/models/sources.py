from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.common import RunStatus, SourceHealth, uuid_string, utc_now


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
    health: Mapped[SourceHealth] = mapped_column(Enum(SourceHealth, native_enum=False), default=SourceHealth.UNAVAILABLE)
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
    processing_status: Mapped[RunStatus] = mapped_column(Enum(RunStatus, native_enum=False))

    source: Mapped[DataSource] = relationship(back_populates="versions")


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_string)
    source_id: Mapped[str] = mapped_column(ForeignKey("data_sources.id"), index=True)
    dataset_version_id: Mapped[str | None] = mapped_column(ForeignKey("dataset_versions.id"))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[RunStatus] = mapped_column(Enum(RunStatus, native_enum=False))
    records_processed: Mapped[int] = mapped_column(Integer, default=0)
    records_added: Mapped[int] = mapped_column(Integer, default=0)
    records_removed: Mapped[int] = mapped_column(Integer, default=0)
    records_changed: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)


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
