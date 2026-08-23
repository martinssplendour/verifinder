from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path

from app.config import get_settings
from app.services.dataset_utils import sha256_file
from app.services.gias_ingestion import inspect_gias_file
from app.services.gias_loader import load_gias_snapshot
from app.services.ofsted_ingestion import inspect_ofsted_file
from app.services.ofsted_loader import load_ofsted_snapshot

from ._shared import _preserve


def ingest_school_file(source_file: Path, published_on: date | None = None) -> dict:
    settings = get_settings()
    retrieved_at = datetime.now(timezone.utc)
    file_hash = sha256_file(source_file)
    destination_dir = Path(settings.raw_data_storage) / "department-for-education" / "gias"
    destination = _preserve(source_file, destination_dir, f"{retrieved_at:%Y%m%dT%H%M%SZ}-edubasealldata-{file_hash[:12]}.csv")
    snapshot = inspect_gias_file(destination)
    result = load_gias_snapshot(snapshot, retrieved_at, published_on)
    manifest = {
        "source": "gias-establishments",
        "retrieved_at": retrieved_at.isoformat(),
        "published_at": published_on.isoformat() if published_on else None,
        "file_hash": snapshot.file_hash,
        "record_count": snapshot.record_count,
        "storage_location": str(destination),
        **result,
    }
    destination.with_suffix(".json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def ingest_ofsted_file(source_file: Path, published_on: date | None = None) -> dict:
    settings = get_settings()
    retrieved_at = datetime.now(timezone.utc)
    file_hash = sha256_file(source_file)
    destination_dir = Path(settings.raw_data_storage) / "ofsted" / "inspections"
    destination = _preserve(source_file, destination_dir, f"{retrieved_at:%Y%m%dT%H%M%SZ}-latest-inspections-{file_hash[:12]}.csv")
    snapshot = inspect_ofsted_file(destination)
    result = load_ofsted_snapshot(snapshot, retrieved_at, published_on)
    manifest = {
        "source": "ofsted-school-inspections",
        "retrieved_at": retrieved_at.isoformat(),
        "published_at": published_on.isoformat() if published_on else None,
        "file_hash": snapshot.file_hash,
        "record_count": snapshot.record_count,
        "storage_location": str(destination),
        **result,
    }
    destination.with_suffix(".json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest
