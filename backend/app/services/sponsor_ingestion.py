import csv
import hashlib
import io
import json
from dataclasses import dataclass
from pathlib import Path

from app.services.normalization import normalise_name


REQUIRED_COLUMN_GROUPS = {
    "organisation": {"Organisation Name", "Organisation", "Organisation name"},
    "town": {"Town/City", "Town / City", "Town"},
    "rating": {"Type & Rating", "Rating", "Sponsor Rating"},
    "route": {"Route", "Route Name"},
}


class SponsorSchemaError(ValueError):
    pass


@dataclass(frozen=True)
class SponsorSnapshot:
    file_hash: str
    records: dict[str, dict]
    columns: dict[str, str]


@dataclass(frozen=True)
class SnapshotDiff:
    added: tuple[str, ...]
    removed: tuple[str, ...]
    changed: tuple[str, ...]


def _resolve_columns(fieldnames: list[str] | None) -> dict[str, str]:
    if not fieldnames:
        raise SponsorSchemaError("The sponsor CSV has no header row.")
    resolved: dict[str, str] = {}
    for purpose, aliases in REQUIRED_COLUMN_GROUPS.items():
        match = next((column for column in fieldnames if column.strip() in aliases), None)
        if not match:
            raise SponsorSchemaError(f"Missing required sponsor column for {purpose}: {sorted(aliases)}")
        resolved[purpose] = match
    return resolved


def parse_sponsor_csv(content: bytes) -> SponsorSnapshot:
    file_hash = hashlib.sha256(content).hexdigest()
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise SponsorSchemaError("Sponsor CSV must be valid UTF-8.") from error
    reader = csv.DictReader(io.StringIO(text))
    columns = _resolve_columns(reader.fieldnames)
    records: dict[str, dict] = {}
    for row_number, row in enumerate(reader, start=2):
        organisation = (row.get(columns["organisation"]) or "").strip()
        if not organisation:
            continue
        record = {
            "organisation_name": organisation,
            "normalised_name": normalise_name(organisation),
            "town_city": (row.get(columns["town"]) or "").strip() or None,
            "county": (row.get("County") or "").strip() or None,
            "sponsor_rating": (row.get(columns["rating"]) or "").strip() or None,
            "routes": [(row.get(columns["route"]) or "").strip()] if (row.get(columns["route"]) or "").strip() else [],
            "raw_records": [row],
        }
        key_payload = "|".join((record["normalised_name"], record["town_city"] or ""))
        key = hashlib.sha256(key_payload.encode("utf-8")).hexdigest()
        if key in records:
            existing = records[key]
            existing["routes"] = sorted(set(existing["routes"] + record["routes"]))
            existing["raw_records"].append(row)
            if record["sponsor_rating"] and not existing["sponsor_rating"]:
                existing["sponsor_rating"] = record["sponsor_rating"]
            continue
        records[key] = record
    if not records:
        raise SponsorSchemaError("The sponsor CSV contains no usable organisation records.")
    return SponsorSnapshot(file_hash=file_hash, records=records, columns=columns)


def diff_snapshots(previous: SponsorSnapshot, current: SponsorSnapshot) -> SnapshotDiff:
    previous_keys = set(previous.records)
    current_keys = set(current.records)
    common = previous_keys & current_keys
    changed = tuple(
        sorted(
            key
            for key in common
            if json.dumps(previous.records[key], sort_keys=True) != json.dumps(current.records[key], sort_keys=True)
        )
    )
    return SnapshotDiff(
        added=tuple(sorted(current_keys - previous_keys)),
        removed=tuple(sorted(previous_keys - current_keys)),
        changed=changed,
    )


def read_snapshot(path: Path) -> SponsorSnapshot:
    return parse_sponsor_csv(path.read_bytes())


def snapshot_from_records(records: list) -> SponsorSnapshot:
    """Rebuild the comparable shape from persisted SponsorRecord rows."""
    mapped = {
        record.source_record_key: {
            "organisation_name": record.organisation_name,
            "normalised_name": record.normalised_name,
            "town_city": record.town_city,
            "county": record.county,
            "sponsor_rating": record.sponsor_rating,
            "routes": sorted(record.routes or []),
            "raw_records": record.raw_record if isinstance(record.raw_record, list) else [],
        }
        for record in records
    }
    return SponsorSnapshot(file_hash="persisted", records=mapped, columns={})
