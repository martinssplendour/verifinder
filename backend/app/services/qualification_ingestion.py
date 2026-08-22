from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.services.dataset_utils import (
    combined_sha256,
    count_csv_rows,
    csv_header,
    csv_rows,
    normalise_identifier,
    parse_bool,
    parse_date,
    parse_float,
    parse_int,
)
from app.services.normalization import normalise_name


QUALIFICATION_REQUIRED = {
    "Qualification Number",
    "Qualification Title",
    "Owner Organisation Recognition Number",
    "Owner Organisation Name",
    "Qualification Status",
}
ORGANISATION_REQUIRED = {"Recognition Number", "Name", "Ofqual Status"}


class QualificationSchemaError(ValueError):
    pass


@dataclass(frozen=True)
class QualificationSnapshot:
    qualifications_path: Path
    organisations_path: Path
    file_hash: str
    qualification_count: int
    organisation_count: int

    @property
    def record_count(self) -> int:
        return self.qualification_count + self.organisation_count


def _require_columns(path: Path, required: set[str], label: str) -> None:
    columns = set(csv_header(path))
    missing = sorted(required - columns)
    if missing:
        raise QualificationSchemaError(f"Missing required {label} columns: {missing}")


def inspect_qualification_files(qualifications_path: Path, organisations_path: Path) -> QualificationSnapshot:
    if not qualifications_path.is_file():
        raise FileNotFoundError(qualifications_path)
    if not organisations_path.is_file():
        raise FileNotFoundError(organisations_path)
    _require_columns(qualifications_path, QUALIFICATION_REQUIRED, "qualification")
    _require_columns(organisations_path, ORGANISATION_REQUIRED, "organisation")
    qualification_count = count_csv_rows(qualifications_path)
    organisation_count = count_csv_rows(organisations_path)
    if qualification_count == 0 or organisation_count == 0:
        raise QualificationSchemaError("The Ofqual files must contain qualification and organisation records.")
    return QualificationSnapshot(
        qualifications_path=qualifications_path,
        organisations_path=organisations_path,
        file_hash=combined_sha256((qualifications_path, organisations_path)),
        qualification_count=qualification_count,
        organisation_count=organisation_count,
    )


def organisation_rows(snapshot: QualificationSnapshot, version_id: str):
    for row in csv_rows(snapshot.organisations_path):
        number = row["Recognition Number"].strip()
        name = row["Name"].strip()
        if not number or not name:
            continue
        yield {
            "dataset_version_id": version_id,
            "recognition_number": number,
            "name": name,
            "normalised_name": normalise_name(name),
            "legal_name": row.get("Legal Name", "").strip() or None,
            "acronym": row.get("Acronym", "").strip() or None,
            "website": row.get("Website", "").strip() or None,
            "postcode": row.get("Head Office Address Postcode", "").strip() or None,
            "ofqual_status": row.get("Ofqual Status", "").strip() or None,
            "ofqual_recognised_from": parse_date(row.get("Ofqual Recognised From")),
            "ofqual_recognised_to": parse_date(row.get("Ofqual Recognised To")),
            "ccea_status": row.get("CCEA Regulation Status", "").strip() or None,
            "raw_record": row,
        }


def qualification_rows(snapshot: QualificationSnapshot, version_id: str):
    for row in csv_rows(snapshot.qualifications_path):
        number = row["Qualification Number"].strip()
        title = row["Qualification Title"].strip()
        organisation_number = row["Owner Organisation Recognition Number"].strip()
        organisation_name = row["Owner Organisation Name"].strip()
        if not number or not title or not organisation_number:
            continue
        yield {
            "dataset_version_id": version_id,
            "qualification_number": number,
            "normalised_number": normalise_identifier(number),
            "title": title,
            "normalised_title": normalise_name(title),
            "awarding_organisation_number": organisation_number,
            "awarding_organisation_name": organisation_name,
            "awarding_organisation_acronym": row.get("Owner Organisation Acronym", "").strip() or None,
            "level": row.get("Qualification Level", "").strip() or None,
            "sub_level": row.get("Qualification Sub Level", "").strip() or None,
            "qualification_type": row.get("Qualification Type", "").strip() or None,
            "sector_subject_area": row.get("Qualification SSA", "").strip() or None,
            "status": row.get("Qualification Status", "").strip() or None,
            "regulation_start_date": parse_date(row.get("Regulation Start Date")),
            "operational_start_date": parse_date(row.get("Operational Start Date")),
            "operational_end_date": parse_date(row.get("Operational End Date")),
            "certification_end_date": parse_date(row.get("Certification End Date")),
            "total_credits": parse_float(row.get("Total Credits")),
            "total_qualification_time": parse_int(row.get("Total Qualification Time")),
            "guided_learning_hours": parse_int(row.get("Guided Learning Hours")),
            "offered_in_england": parse_bool(row.get("Offered In England")),
            "offered_in_northern_ireland": parse_bool(row.get("Offered In Northern Ireland")),
            "grading_type": row.get("Overall Grading Type", "").strip() or None,
            "assessment_methods": row.get("Assessment Methods", "").strip() or None,
            "specification_url": row.get("Link To Specification", "").strip() or None,
            "raw_record": row,
        }
