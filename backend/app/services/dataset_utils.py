from __future__ import annotations

import csv
import hashlib
import re
from collections.abc import Iterable, Iterator
from datetime import date
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def combined_sha256(paths: Iterable[Path]) -> str:
    digest = hashlib.sha256()
    for path in paths:
        digest.update(bytes.fromhex(sha256_file(path)))
    return digest.hexdigest()


def csv_rows(path: Path) -> Iterator[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        yield from csv.DictReader(source)


def csv_header(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        return next(csv.reader(source), [])


def count_csv_rows(path: Path) -> int:
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.reader(source)
        next(reader, None)
        return sum(1 for _ in reader)


def chunks(items: Iterable[dict], size: int = 2_000) -> Iterator[list[dict]]:
    batch: list[dict] = []
    for item in items:
        batch.append(item)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch


def parse_date(value: str | None) -> date | None:
    cleaned = (value or "").strip()
    if not cleaned:
        return None
    try:
        return date.fromisoformat(cleaned[:10])
    except ValueError:
        return None


def parse_bool(value: str | None) -> bool | None:
    cleaned = (value or "").strip().lower()
    if cleaned in {"yes", "true", "1", "y"}:
        return True
    if cleaned in {"no", "false", "0", "n"}:
        return False
    return None


def parse_int(value: str | None) -> int | None:
    cleaned = (value or "").strip()
    if not cleaned:
        return None
    try:
        return int(float(cleaned))
    except ValueError:
        return None


def parse_float(value: str | None) -> float | None:
    cleaned = (value or "").strip()
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def normalise_identifier(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def normalise_postcode(value: str | None) -> str | None:
    cleaned = normalise_identifier(value or "")
    return cleaned.upper() or None


POSTCODE_PATTERN = re.compile(r"^[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}$", re.IGNORECASE)


def looks_like_postcode(value: str | None) -> bool:
    """Whether a search term is shaped like a UK postcode rather than a name."""
    return bool(POSTCODE_PATTERN.fullmatch((value or "").strip()))
