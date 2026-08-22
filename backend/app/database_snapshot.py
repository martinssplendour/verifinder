from __future__ import annotations

import gzip
import hashlib
import os
import shutil
import sqlite3
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from sqlalchemy.engine import make_url

from app.config import get_settings


SQLITE_HEADER = b"SQLite format 3\x00"
DOWNLOAD_CHUNK_SIZE = 1024 * 1024


def _database_path(database_url: str) -> Path:
    parsed = make_url(database_url)
    if parsed.get_backend_name() != "sqlite" or not parsed.database or parsed.database == ":memory:":
        raise ValueError("Snapshot bootstrapping requires a file-backed SQLite DATABASE_URL.")
    return Path(parsed.database).expanduser().resolve()


def _is_valid_database(path: Path) -> bool:
    if not path.is_file() or path.stat().st_size < len(SQLITE_HEADER):
        return False
    with path.open("rb") as handle:
        if handle.read(len(SQLITE_HEADER)) != SQLITE_HEADER:
            return False
    try:
        with sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True) as connection:
            return connection.execute("PRAGMA quick_check").fetchone() == ("ok",)
    except sqlite3.DatabaseError:
        return False


def _validate_snapshot_url(value: str) -> str:
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("DATABASE_SNAPSHOT_URL must be an HTTPS URL.")
    return value


def _download_snapshot(url: str, destination: Path, expected_sha256: str) -> None:
    digest = hashlib.sha256()
    with httpx.stream("GET", url, follow_redirects=True, timeout=httpx.Timeout(300, connect=20)) as response:
        response.raise_for_status()
        with destination.open("xb") as output:
            for chunk in response.iter_bytes(DOWNLOAD_CHUNK_SIZE):
                output.write(chunk)
                digest.update(chunk)
    if digest.hexdigest().lower() != expected_sha256.lower():
        raise ValueError("The database snapshot checksum did not match the configured SHA-256.")


def _expand_snapshot(archive: Path, destination: Path) -> None:
    with gzip.open(archive, "rb") as source, destination.open("xb") as output:
        shutil.copyfileobj(source, output, length=DOWNLOAD_CHUNK_SIZE)


def bootstrap_database() -> Path:
    settings = get_settings()
    destination = _database_path(settings.database_url)
    if _is_valid_database(destination):
        return destination

    snapshot_url = os.getenv("DATABASE_SNAPSHOT_URL", "").strip()
    expected_sha256 = os.getenv("DATABASE_SNAPSHOT_SHA256", "").strip()
    if not snapshot_url or len(expected_sha256) != 64:
        raise RuntimeError(
            "The database is missing and DATABASE_SNAPSHOT_URL / DATABASE_SNAPSHOT_SHA256 are not configured."
        )
    snapshot_url = _validate_snapshot_url(snapshot_url)
    destination.parent.mkdir(parents=True, exist_ok=True)
    archive = destination.with_name(f".{destination.name}.snapshot.gz")
    expanded = destination.with_name(f".{destination.name}.expanded")
    for temporary in (archive, expanded):
        temporary.unlink(missing_ok=True)
    try:
        _download_snapshot(snapshot_url, archive, expected_sha256)
        _expand_snapshot(archive, expanded)
        if not _is_valid_database(expanded):
            raise ValueError("The expanded snapshot is not a valid SQLite database.")
        os.replace(expanded, destination)
    finally:
        archive.unlink(missing_ok=True)
        expanded.unlink(missing_ok=True)
    return destination


if __name__ == "__main__":
    database = bootstrap_database()
    print(f"VeriFinder database ready at {database} ({database.stat().st_size} bytes).")
