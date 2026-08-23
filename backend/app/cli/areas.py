from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path

from app.config import get_settings
from app.services.dataset_utils import sha256_file
from app.services.postcode_ingestion import inspect_postcode_archive
from app.services.postcode_loader import load_postcode_snapshot

from ._shared import _preserve


def ingest_postcode_file(source_file: Path, published_on: date | None = None) -> dict:
    settings = get_settings()
    retrieved_at = datetime.now(timezone.utc)
    file_hash = sha256_file(source_file)
    destination_dir = Path(settings.raw_data_storage) / "ordnance-survey" / "code-point-open"
    destination = _preserve(source_file, destination_dir, f"{retrieved_at:%Y%m%dT%H%M%SZ}-code-point-{file_hash[:12]}.zip")
    snapshot = inspect_postcode_archive(destination)
    result = load_postcode_snapshot(snapshot, retrieved_at, published_on)
    manifest = {
        "source": "os-code-point-open",
        "retrieved_at": retrieved_at.isoformat(),
        "published_at": published_on.isoformat() if published_on else None,
        "file_hash": snapshot.file_hash,
        "record_count": snapshot.record_count,
        "storage_location": str(destination),
        **result,
    }
    destination.with_suffix(".json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest
