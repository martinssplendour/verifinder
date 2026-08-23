from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path

from app.config import get_settings
from app.services.study_ingestion import inspect_ofs_register, inspect_student_sponsors
from app.services.study_loader import load_ofs_register, load_student_sponsors

from ._shared import _preserve


def ingest_study_provider_files(student_file: Path, ofs_file: Path, published_on: date | None = None) -> dict:
    settings = get_settings()
    retrieved_at = datetime.now(timezone.utc)
    student_dir = Path(settings.raw_data_storage) / "home-office" / "student-sponsors"
    ofs_dir = Path(settings.raw_data_storage) / "office-for-students" / "register"
    student = _preserve(student_file, student_dir, f"{retrieved_at:%Y%m%dT%H%M%SZ}-student-sponsors.csv")
    ofs = _preserve(ofs_file, ofs_dir, f"{retrieved_at:%Y%m%dT%H%M%SZ}-ofs-register.xlsx")
    student_snapshot = inspect_student_sponsors(student)
    ofs_snapshot = inspect_ofs_register(ofs)
    student_result = load_student_sponsors(student_snapshot, retrieved_at, published_on)
    ofs_result = load_ofs_register(ofs_snapshot, retrieved_at, published_on)
    manifest = {
        "source": "study-providers",
        "retrieved_at": retrieved_at.isoformat(),
        "published_at": published_on.isoformat() if published_on else None,
        "student_sponsors": {"storage_location": str(student), **student_result},
        "ofs_register": {"storage_location": str(ofs), **ofs_result},
    }
    student.with_suffix(".json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest
