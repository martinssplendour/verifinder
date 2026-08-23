from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path

from app.config import get_settings
from app.services.dataset_utils import sha256_file
from app.services.qualification_ingestion import inspect_qualification_files
from app.services.qualification_loader import load_qualification_snapshot
from app.services.qualification_expansion_ingestion import inspect_welsh_qualifications
from app.services.qualification_expansion_loader import load_welsh_qualifications
from app.services.qualification_unit_ingestion import inspect_qualification_unit_files
from app.services.qualification_unit_loader import load_qualification_units

from ._shared import _preserve


def ingest_qualification_files(
    qualifications_file: Path,
    organisations_file: Path,
    published_on: date | None = None,
) -> dict:
    settings = get_settings()
    retrieved_at = datetime.now(timezone.utc)
    destination_dir = Path(settings.raw_data_storage) / "ofqual"
    qualification_hash = sha256_file(qualifications_file)
    organisation_hash = sha256_file(organisations_file)
    qualifications = _preserve(
        qualifications_file,
        destination_dir,
        f"{retrieved_at:%Y%m%dT%H%M%SZ}-qualifications-{qualification_hash[:12]}.csv",
    )
    organisations = _preserve(
        organisations_file,
        destination_dir,
        f"{retrieved_at:%Y%m%dT%H%M%SZ}-organisations-{organisation_hash[:12]}.csv",
    )
    snapshot = inspect_qualification_files(qualifications, organisations)
    result = load_qualification_snapshot(snapshot, retrieved_at, published_on)
    manifest = {
        "source": "ofqual-register",
        "retrieved_at": retrieved_at.isoformat(),
        "published_at": published_on.isoformat() if published_on else None,
        "file_hash": snapshot.file_hash,
        "qualification_count": snapshot.qualification_count,
        "organisation_count": snapshot.organisation_count,
        "storage_locations": {"qualifications": str(qualifications), "organisations": str(organisations)},
        **result,
    }
    manifest_path = qualifications.with_suffix(".json")
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def ingest_qualification_unit_files(units_file: Path, mappings_file: Path, published_on: date | None = None) -> dict:
    settings = get_settings()
    retrieved_at = datetime.now(timezone.utc)
    destination_dir = Path(settings.raw_data_storage) / "ofqual" / "expansion"
    units = _preserve(units_file, destination_dir, f"{retrieved_at:%Y%m%dT%H%M%SZ}-units.csv")
    mappings = _preserve(mappings_file, destination_dir, f"{retrieved_at:%Y%m%dT%H%M%SZ}-qualification-units.csv")
    snapshot = inspect_qualification_unit_files(units, mappings)
    result = load_qualification_units(snapshot, retrieved_at, published_on)
    manifest = {
        "source": "ofqual-qualification-units",
        "retrieved_at": retrieved_at.isoformat(),
        "published_at": published_on.isoformat() if published_on else None,
        "storage_locations": {"units": str(units), "mappings": str(mappings)},
        "unit_count": snapshot.unit_count,
        "mapping_count": snapshot.mapping_count,
        **result,
    }
    units.with_suffix(".json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def ingest_welsh_qualification_file(source_file: Path, published_on: date | None = None) -> dict:
    settings = get_settings()
    retrieved_at = datetime.now(timezone.utc)
    destination_dir = Path(settings.raw_data_storage) / "qualifications-wales"
    destination = _preserve(source_file, destination_dir, f"{retrieved_at:%Y%m%dT%H%M%SZ}-qiw-complete-en.csv")
    snapshot = inspect_welsh_qualifications(destination)
    result = load_welsh_qualifications(snapshot, retrieved_at, published_on)
    manifest = {
        "source": "qualifications-wales-qiw",
        "retrieved_at": retrieved_at.isoformat(),
        "published_at": published_on.isoformat() if published_on else None,
        "storage_location": str(destination),
        **result,
    }
    destination.with_suffix(".json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest
