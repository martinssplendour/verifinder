from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path

from app.config import get_settings
from app.services.property_ingestion import inspect_property_files
from app.services.property_loader import load_property_snapshot

from ._shared import _preserve


def ingest_property_files(source_files: list[Path], published_on: date | None = None) -> dict:
    settings = get_settings()
    retrieved_at = datetime.now(timezone.utc)
    destination_dir = Path(settings.raw_data_storage) / "hm-land-registry" / "price-paid"
    preserved = [
        _preserve(source_file, destination_dir, f"{retrieved_at:%Y%m%dT%H%M%SZ}-{source_file.name}")
        for source_file in source_files
    ]
    snapshot = inspect_property_files(preserved)
    result = load_property_snapshot(snapshot, retrieved_at, published_on)
    manifest = {
        "source": "hm-land-registry-price-paid",
        "retrieved_at": retrieved_at.isoformat(),
        "published_at": published_on.isoformat() if published_on else None,
        "file_hash": snapshot.file_hash,
        "record_count": snapshot.record_count,
        "storage_locations": [str(path) for path in preserved],
        **result,
    }
    preserved[0].with_suffix(".json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest
