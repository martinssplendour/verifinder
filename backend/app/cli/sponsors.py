from __future__ import annotations

import json
import shutil
from datetime import date, datetime, timezone
from pathlib import Path

from app.config import get_settings
from app.services.sponsor_ingestion import read_snapshot
from app.services.sponsor_loader import load_snapshot


def ingest_sponsor_file(source_file: Path, published_on: date | None = None) -> dict:
    settings = get_settings()
    snapshot = read_snapshot(source_file)
    retrieved_at = datetime.now(timezone.utc)
    destination_dir = Path(settings.raw_data_storage) / "home-office" / "worker-sponsors"
    destination_dir.mkdir(parents=True, exist_ok=True)
    if source_file.resolve().parent == destination_dir.resolve():
        destination = source_file.resolve()
    else:
        destination = destination_dir / f"{retrieved_at:%Y%m%dT%H%M%SZ}-{snapshot.file_hash[:12]}.csv"
    if not destination.exists():
        shutil.copy2(source_file, destination)
    load_result = load_snapshot(snapshot, destination, retrieved_at, published_on)
    manifest = {
        "source": "home-office-worker-sponsors",
        "retrieved_at": retrieved_at.isoformat(),
        "file_hash": snapshot.file_hash,
        "record_count": len(snapshot.records),
        "storage_location": str(destination),
        "published_at": published_on.isoformat() if published_on else None,
        **load_result,
    }
    manifest_path = destination.with_suffix(".json")
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest
