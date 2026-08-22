from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from app.services.dataset_utils import normalise_postcode, parse_int, sha256_file
from app.services.normalization import normalise_name


ENCODING = "cp1252"


class GiasSchemaError(ValueError):
    pass


@dataclass(frozen=True)
class GiasSnapshot:
    path: Path
    file_hash: str
    record_count: int


def _parse_gias_date(value: str | None) -> date | None:
    cleaned = (value or "").strip()
    if not cleaned:
        return None
    try:
        return datetime.strptime(cleaned, "%d-%m-%Y").date()
    except ValueError:
        return None


def inspect_gias_file(path: Path) -> GiasSnapshot:
    if not path.is_file():
        raise FileNotFoundError(path)
    record_count = 0
    with path.open("r", encoding=ENCODING, newline="") as source:
        reader = csv.DictReader(source)
        if not reader.fieldnames or "URN" not in reader.fieldnames:
            raise GiasSchemaError("The GIAS establishment CSV is missing the required URN column.")
        for row in reader:
            if (row.get("URN") or "").strip():
                record_count += 1
    if record_count == 0:
        raise GiasSchemaError("The GIAS establishment CSV contains no establishment records.")
    return GiasSnapshot(path=path, file_hash=sha256_file(path), record_count=record_count)


def gias_rows(snapshot: GiasSnapshot, version_id: str):
    with snapshot.path.open("r", encoding=ENCODING, newline="") as source:
        for row in csv.DictReader(source):
            urn = (row.get("URN") or "").strip()
            establishment_name = (row.get("EstablishmentName") or "").strip()
            if not urn or not establishment_name:
                continue
            postcode = (row.get("Postcode") or "").strip() or None
            yield {
                "dataset_version_id": version_id,
                "urn": urn,
                "la_name": (row.get("LA (name)") or "").strip() or None,
                "establishment_name": establishment_name,
                "normalised_name": normalise_name(establishment_name),
                "type_name": (row.get("TypeOfEstablishment (name)") or "").strip() or None,
                "type_group_name": (row.get("EstablishmentTypeGroup (name)") or "").strip() or None,
                "status_name": (row.get("EstablishmentStatus (name)") or "").strip() or None,
                "phase_name": (row.get("PhaseOfEducation (name)") or "").strip() or None,
                "statutory_low_age": parse_int(row.get("StatutoryLowAge")),
                "statutory_high_age": parse_int(row.get("StatutoryHighAge")),
                "gender_name": (row.get("Gender (name)") or "").strip() or None,
                "religious_character_name": (row.get("ReligiousCharacter (name)") or "").strip() or None,
                "school_capacity": parse_int(row.get("SchoolCapacity")),
                "number_of_pupils": parse_int(row.get("NumberOfPupils")),
                "ukprn": (row.get("UKPRN") or "").strip() or None,
                "open_date": _parse_gias_date(row.get("OpenDate")),
                "close_date": _parse_gias_date(row.get("CloseDate")),
                "street": (row.get("Street") or "").strip() or None,
                "locality": (row.get("Locality") or "").strip() or None,
                "town": (row.get("Town") or "").strip() or None,
                "county_name": (row.get("County (name)") or "").strip() or None,
                "postcode": postcode,
                "normalised_postcode": normalise_postcode(postcode),
                "website": (row.get("SchoolWebsite") or "").strip() or None,
                "telephone": (row.get("TelephoneNum") or "").strip() or None,
                "head_first_name": (row.get("HeadFirstName") or "").strip() or None,
                "head_last_name": (row.get("HeadLastName") or "").strip() or None,
                "region_name": (row.get("GOR (name)") or "").strip() or None,
                "country_name": (row.get("Country (name)") or "").strip() or None,
                "raw_record": row,
            }
