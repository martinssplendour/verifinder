from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from app.services.dataset_utils import parse_bool, sha256_file


ENCODING = "cp1252"


class OfstedSchemaError(ValueError):
    pass


@dataclass(frozen=True)
class OfstedSnapshot:
    path: Path
    file_hash: str
    record_count: int


def _clean(value: str | None) -> str | None:
    cleaned = (value or "").strip()
    if not cleaned or cleaned.upper() == "NULL":
        return None
    return cleaned


def _parse_ofsted_date(value: str | None) -> date | None:
    cleaned = _clean(value)
    if not cleaned:
        return None
    try:
        return datetime.strptime(cleaned, "%d/%m/%Y").date()
    except ValueError:
        return None


def _parse_ofsted_bool(value: str | None) -> bool | None:
    return parse_bool(_clean(value))


def inspect_ofsted_file(path: Path) -> OfstedSnapshot:
    if not path.is_file():
        raise FileNotFoundError(path)
    record_count = 0
    with path.open("r", encoding=ENCODING, newline="") as source:
        reader = csv.DictReader(source)
        if not reader.fieldnames or "URN" not in reader.fieldnames:
            raise OfstedSchemaError("The Ofsted inspections CSV is missing the required URN column.")
        for row in reader:
            if (row.get("URN") or "").strip():
                record_count += 1
    if record_count == 0:
        raise OfstedSchemaError("The Ofsted inspections CSV contains no inspection records.")
    return OfstedSnapshot(path=path, file_hash=sha256_file(path), record_count=record_count)


def ofsted_rows(snapshot: OfstedSnapshot, version_id: str):
    with snapshot.path.open("r", encoding=ENCODING, newline="") as source:
        for row in csv.DictReader(source):
            urn = (row.get("URN") or "").strip()
            if not urn:
                continue
            postcode = _clean(row.get("Postcode"))
            yield {
                "dataset_version_id": version_id,
                "urn": urn,
                "school_name": _clean(row.get("School name")),
                "ofsted_phase": _clean(row.get("Ofsted phase")),
                "local_authority": _clean(row.get("Local authority")),
                "region": _clean(row.get("Region")),
                "postcode": postcode,
                "most_recent_category_of_concern": _clean(row.get("Most recent category of concern")),
                "full_inspection_number": _clean(row.get("Inspection number of latest full inspection")),
                "full_inspection_type": _clean(row.get("Inspection type")),
                "full_inspection_start_date": _parse_ofsted_date(row.get("Inspection start date")),
                "full_inspection_publication_date": _parse_ofsted_date(row.get("Publication date")),
                "safeguarding_standards": _clean(row.get("Safeguarding standards")),
                "inclusion": _clean(row.get("Inclusion")),
                "curriculum_and_teaching": _clean(row.get("Curriculum and teaching")),
                "achievement": _clean(row.get("Achievement")),
                "attendance_and_behaviour": _clean(row.get("Attendance and behaviour")),
                "personal_development_and_wellbeing": _clean(row.get("Personal development and wellbeing")),
                "early_years": _clean(row.get("Early years (where applicable)")),
                "post_16_provision": _clean(row.get("Post-16 provision (where applicable)")),
                "leadership_and_governance": _clean(row.get("Leadership and governance")),
                "oeif_start_date": _parse_ofsted_date(row.get("Inspection start date of latest OEIF graded inspection")),
                "oeif_publication_date": _parse_ofsted_date(row.get("Publication date of latest OEIF graded inspection")),
                "oeif_overall_effectiveness": _clean(row.get("Latest OEIF overall effectiveness")),
                "oeif_safeguarding_effective": _parse_ofsted_bool(row.get("Latest OEIF  safeguarding is effective?")),
                "ungraded_inspection_date": _parse_ofsted_date(row.get("Date of latest ungraded inspection")),
                "ungraded_publication_date": _parse_ofsted_date(row.get("Ungraded inspection publication date")),
                "ungraded_overall_outcome": _clean(row.get("Ungraded inspection overall outcome")),
                "raw_record": row,
            }
