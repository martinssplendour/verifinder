from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from app.services.dataset_utils import count_csv_rows, csv_header, csv_rows, normalise_identifier, parse_bool, sha256_file
from app.services.normalization import normalise_name


class QualificationExpansionSchemaError(ValueError):
    pass


@dataclass(frozen=True)
class WelshQualificationSnapshot:
    path: Path
    file_hash: str
    record_count: int


QIW_REQUIRED = {
    "QW Approval/Designation No.",
    "Awarding Body",
    "English qualification title",
    "Qualification number",
    "Status",
}


def inspect_welsh_qualifications(path: Path) -> WelshQualificationSnapshot:
    if not path.is_file():
        raise FileNotFoundError(path)
    missing = sorted(QIW_REQUIRED - set(csv_header(path)))
    if missing:
        raise QualificationExpansionSchemaError(f"Missing required QiW columns: {missing}")
    record_count = count_csv_rows(path)
    if record_count == 0:
        raise QualificationExpansionSchemaError("The QiW export contains no qualification records.")
    return WelshQualificationSnapshot(path, sha256_file(path), record_count)


def _date(value: str | None) -> date | None:
    text = (value or "").strip()
    if not text:
        return None
    for pattern in ("%d/%m/%Y", "%Y-%m-%d", "%d/%m/%Y %H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(text, pattern).date()
        except ValueError:
            continue
    return None


def _languages(value: str | None) -> list[str]:
    text = (value or "").lower()
    result = []
    if "english" in text:
        result.append("English")
    if "welsh" in text:
        result.append("Welsh")
    return result


def welsh_qualification_rows(snapshot: WelshQualificationSnapshot, version_id: str):
    seen: set[str] = set()
    for row in csv_rows(snapshot.path):
        approval_number = row.get("QW Approval/Designation No.", "").strip()
        qualification_number = row.get("Qualification number", "").strip()
        title = row.get("English qualification title", "").strip()
        awarding_body = row.get("Awarding Body", "").strip()
        if not title:
            continue
        identity = approval_number or qualification_number or hashlib.sha1(
            f"{title}|{awarding_body}".encode("utf-8")
        ).hexdigest()
        if identity in seen:
            continue
        seen.add(identity)
        public_funded = parse_bool(row.get("Public Funded"))
        if public_funded is None:
            public_funded = row.get("Review type", "").strip().lower() in {"approval", "designation"}
        yield {
            "dataset_version_id": version_id,
            "source_record_key": identity,
            "regulator": "Qualifications Wales",
            "jurisdiction": "Wales",
            "qualification_number": qualification_number or None,
            "normalised_number": normalise_identifier(qualification_number) or None,
            "approval_number": approval_number or None,
            "title": title,
            "normalised_title": normalise_name(title),
            "awarding_organisation_name": awarding_body or None,
            "normalised_organisation_name": normalise_name(awarding_body) or None,
            "level": row.get("Qualification level", "").strip() or None,
            "qualification_type": row.get("Qualification type", "").strip() or None,
            "status": row.get("Status", "").strip() or None,
            "languages": _languages(row.get("Language")),
            "review_type": row.get("Review type", "").strip() or None,
            "start_date": _date(row.get("Designation/Approval Start Date") or row.get("Start date")),
            "end_date": _date(row.get("Typical Designation/Approval final start date")),
            "certification_end_date": _date(row.get("Designation/Approval Certification End Date")),
            "eligible_public_funding": public_funded,
        }
