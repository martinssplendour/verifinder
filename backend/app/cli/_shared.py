from __future__ import annotations

import shutil
from pathlib import Path


def _preserve(source_file: Path, destination_dir: Path, filename: str) -> Path:
    destination_dir.mkdir(parents=True, exist_ok=True)
    if source_file.resolve().parent == destination_dir.resolve():
        return source_file.resolve()
    destination = destination_dir / filename
    if not destination.exists():
        shutil.copy2(source_file, destination)
    return destination
