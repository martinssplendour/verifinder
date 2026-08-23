from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path

from app.config import get_settings
from app.services.dataset_utils import sha256_file
from app.services.food_ingestion import inspect_food_file
from app.services.food_loader import load_food_snapshot

from ._shared import _preserve


def ingest_food_file(source_file: Path, published_on: date | None = None) -> dict:
    settings = get_settings()
    retrieved_at = datetime.now(timezone.utc)
    file_hash = sha256_file(source_file)
    destination_dir = Path(settings.raw_data_storage) / "food-standards-agency" / "food-hygiene"
    destination = _preserve(
        source_file,
        destination_dir,
        f"{retrieved_at:%Y%m%dT%H%M%SZ}-fhrs-{file_hash[:12]}.csv",
    )
    snapshot = inspect_food_file(destination)
    result = load_food_snapshot(snapshot, retrieved_at, published_on)
    manifest = {
        "source": "fsa-food-hygiene",
        "retrieved_at": retrieved_at.isoformat(),
        "published_at": published_on.isoformat() if published_on else None,
        "file_hash": snapshot.file_hash,
        "record_count": snapshot.record_count,
        "storage_location": str(destination),
        **result,
    }
    destination.with_suffix(".json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest
