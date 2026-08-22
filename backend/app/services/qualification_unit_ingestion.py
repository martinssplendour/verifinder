from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.services.dataset_utils import (
    combined_sha256,
    count_csv_rows,
    csv_header,
    csv_rows,
    normalise_identifier,
    parse_float,
    parse_int,
)
from app.services.normalization import normalise_name


class QualificationUnitSchemaError(ValueError):
    pass


@dataclass(frozen=True)
class QualificationUnitSnapshot:
    units_path: Path
    mappings_path: Path
    file_hash: str
    unit_count: int
    mapping_count: int

    @property
    def record_count(self) -> int:
        return self.unit_count + self.mapping_count


def inspect_qualification_unit_files(units_path: Path, mappings_path: Path) -> QualificationUnitSnapshot:
    for path in (units_path, mappings_path):
        if not path.is_file():
            raise FileNotFoundError(path)
    unit_required = {"Unit Key", "Title"}
    mapping_required = {"Unit Key", "Qualification Number"}
    unit_missing = sorted(unit_required - set(csv_header(units_path)))
    mapping_missing = sorted(mapping_required - set(csv_header(mappings_path)))
    if unit_missing or mapping_missing:
        raise QualificationUnitSchemaError(
            f"Missing Ofqual unit columns: units={unit_missing}, mappings={mapping_missing}"
        )
    unit_count = count_csv_rows(units_path)
    mapping_count = count_csv_rows(mappings_path)
    if unit_count == 0 or mapping_count == 0:
        raise QualificationUnitSchemaError("The Ofqual unit extracts contain no records.")
    return QualificationUnitSnapshot(
        units_path=units_path,
        mappings_path=mappings_path,
        file_hash=combined_sha256((units_path, mappings_path)),
        unit_count=unit_count,
        mapping_count=mapping_count,
    )


def unit_rows(snapshot: QualificationUnitSnapshot, version_id: str):
    for row in csv_rows(snapshot.units_path):
        unit_key = row.get("Unit Key", "").strip()
        title = row.get("Title", "").strip()
        if not unit_key or not title:
            continue
        yield {
            "dataset_version_id": version_id,
            "unit_key": unit_key,
            "unit_reference": row.get("Unique Reference Number", "").strip() or None,
            "title": title,
            "normalised_title": normalise_name(title),
            "level": row.get("Unit Level", "").strip() or None,
            "credit_value": parse_float(row.get("Unit Credit Value")),
            "guided_learning_hours": parse_int(row.get("Guided Learning Hours")),
        }


def unit_mapping_rows(snapshot: QualificationUnitSnapshot, version_id: str):
    for row in csv_rows(snapshot.mappings_path):
        unit_key = row.get("Unit Key", "").strip()
        qualification_number = row.get("Qualification Number", "").strip()
        if not unit_key or not qualification_number:
            continue
        yield {
            "dataset_version_id": version_id,
            "qualification_number": qualification_number,
            "normalised_qualification_number": normalise_identifier(qualification_number),
            "unit_key": unit_key,
        }
