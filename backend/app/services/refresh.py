from __future__ import annotations

import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

from app.cli import (
    ingest_food_file,
    ingest_ofsted_file,
    ingest_postcode_file,
    ingest_property_files,
    ingest_qualification_files,
    ingest_qualification_unit_files,
    ingest_school_file,
    ingest_sponsor_file,
    ingest_study_provider_files,
    ingest_welsh_qualification_file,
)
from app.billing_database import BillingSessionLocal
from app.database import SessionLocal
from app.services.watchlists import scan_for_changes
from app.models import DataSource
from app.services.food_loader import DATA_URL as FOOD_DATA_URL
from app.services.food_loader import SOURCE_ID as FOOD_SOURCE_ID
from app.services.gias_loader import SOURCE_ID as GIAS_SOURCE_ID
from app.services.govuk_content import resolve_latest_csv_attachment
from app.services.ofsted_loader import SOURCE_ID as OFSTED_SOURCE_ID
from app.services.postcode_loader import DATA_URL as POSTCODE_DATA_URL
from app.services.postcode_loader import SOURCE_ID as POSTCODE_SOURCE_ID
from app.services.property_loader import SOURCE_ID as PROPERTY_SOURCE_ID
from app.services.qualification_expansion_loader import QIW_DATA_URL, QIW_SOURCE_ID
from app.services.qualification_loader import DATA_URL as OFQUAL_QUALIFICATIONS_URL
from app.services.qualification_loader import SOURCE_ID as OFQUAL_SOURCE_ID
from app.services.qualification_unit_loader import DATA_URL as OFQUAL_UNITS_URL
from app.services.qualification_unit_loader import SOURCE_ID as OFQUAL_UNIT_SOURCE_ID
from app.services.source_fetch import SourceFetchError, download_bytes
from app.services.sponsor_loader import SOURCE_ID as SPONSOR_SOURCE_ID
from app.services.study_loader import OFS_DATA_URL, OFS_SOURCE_ID, STUDENT_SOURCE_ID


OFQUAL_ORGANISATIONS_URL = "https://downloads.find-a-qualification.services.ofqual.gov.uk/extracts/Organisations.csv"
OFQUAL_UNIT_MAPPINGS_URL = "https://downloads.find-a-qualification.services.ofqual.gov.uk/extracts/QualificationUnits.csv"
LAND_REGISTRY_BASE = "https://price-paid-data.publicdata.landregistry.gov.uk"
GIAS_BASE = "https://ea-edubase-api-prod.azurewebsites.net/edubase/downloads/public"


def _write_temp(directory: Path, name: str, content: bytes) -> Path:
    path = directory / name
    path.write_bytes(content)
    return path


def _refresh_worker_sponsors(directory: Path) -> dict:
    url, _ = resolve_latest_csv_attachment("government/publications/register-of-licensed-sponsors-workers")
    path = _write_temp(directory, "worker-sponsors.csv", download_bytes(url))
    return ingest_sponsor_file(path)


def _refresh_ofqual(directory: Path) -> dict:
    qualifications = _write_temp(directory, "qualifications.csv", download_bytes(OFQUAL_QUALIFICATIONS_URL))
    organisations = _write_temp(directory, "organisations.csv", download_bytes(OFQUAL_ORGANISATIONS_URL))
    return ingest_qualification_files(qualifications, organisations)


def _refresh_ofqual_units(directory: Path) -> dict:
    units = _write_temp(directory, "units.csv", download_bytes(OFQUAL_UNITS_URL))
    mappings = _write_temp(directory, "qualification-units.csv", download_bytes(OFQUAL_UNIT_MAPPINGS_URL))
    return ingest_qualification_unit_files(units, mappings)


def _refresh_qiw(directory: Path) -> dict:
    path = _write_temp(directory, "qiw-complete-en.csv", download_bytes(QIW_DATA_URL))
    return ingest_welsh_qualification_file(path)


def _refresh_food(directory: Path) -> dict:
    path = _write_temp(directory, "fhrs-all-en-GB.csv", download_bytes(FOOD_DATA_URL))
    return ingest_food_file(path)


def _refresh_postcodes(directory: Path) -> dict:
    path = _write_temp(directory, "code-point-open.zip", download_bytes(POSTCODE_DATA_URL))
    return ingest_postcode_file(path)


def _refresh_property(directory: Path) -> dict:
    files = [
        _write_temp(directory, f"pp-{year}.csv", download_bytes(f"{LAND_REGISTRY_BASE}/pp-{year}.csv"))
        for year in (2025, 2026)
    ]
    return ingest_property_files(files)


def _refresh_study_providers(directory: Path) -> dict:
    student_url, _ = resolve_latest_csv_attachment("government/publications/register-of-licensed-sponsors-students")
    student = _write_temp(directory, "student-sponsors.csv", download_bytes(student_url))
    ofs = _write_temp(directory, "ofs-register.xlsx", download_bytes(OFS_DATA_URL))
    return ingest_study_provider_files(student, ofs)


def _refresh_gias(directory: Path) -> dict:
    today = datetime.now(timezone.utc).date()
    for offset in range(0, 8):
        candidate = today - timedelta(days=offset)
        url = f"{GIAS_BASE}/edubasealldata{candidate:%Y%m%d}.csv"
        try:
            content = download_bytes(url)
        except SourceFetchError:
            continue
        if content[:1] == b"<":
            continue
        path = _write_temp(directory, "edubasealldata.csv", content)
        return ingest_school_file(path, candidate)
    raise RuntimeError("No GIAS establishment CSV was found in the last 8 days.")


def _refresh_ofsted(directory: Path) -> dict:
    url, _ = resolve_latest_csv_attachment(
        "government/statistical-data-sets/monthly-management-information-ofsteds-school-inspections-outcomes",
        title_contains="latest inspections",
    )
    path = _write_temp(directory, "ofsted-latest-inspections.csv", download_bytes(url))
    return ingest_ofsted_file(path)


@dataclass(frozen=True)
class RefreshSpec:
    cadence: timedelta
    refresh: Callable[[Path], dict]


REFRESH_SPECS: dict[str, RefreshSpec] = {
    SPONSOR_SOURCE_ID: RefreshSpec(timedelta(days=1), _refresh_worker_sponsors),
    OFQUAL_SOURCE_ID: RefreshSpec(timedelta(days=1), _refresh_ofqual),
    OFQUAL_UNIT_SOURCE_ID: RefreshSpec(timedelta(days=7), _refresh_ofqual_units),
    QIW_SOURCE_ID: RefreshSpec(timedelta(days=7), _refresh_qiw),
    FOOD_SOURCE_ID: RefreshSpec(timedelta(days=1), _refresh_food),
    POSTCODE_SOURCE_ID: RefreshSpec(timedelta(days=90), _refresh_postcodes),
    PROPERTY_SOURCE_ID: RefreshSpec(timedelta(days=28), _refresh_property),
    STUDENT_SOURCE_ID: RefreshSpec(timedelta(days=1), _refresh_study_providers),
    OFS_SOURCE_ID: RefreshSpec(timedelta(days=7), _refresh_study_providers),
    GIAS_SOURCE_ID: RefreshSpec(timedelta(days=1), _refresh_gias),
    OFSTED_SOURCE_ID: RefreshSpec(timedelta(days=28), _refresh_ofsted),
}


def is_due(last_successful_retrieval: datetime | None, cadence: timedelta, *, now: datetime | None = None) -> bool:
    if last_successful_retrieval is None:
        return True
    if last_successful_retrieval.tzinfo is None:
        last_successful_retrieval = last_successful_retrieval.replace(tzinfo=timezone.utc)
    current = now or datetime.now(timezone.utc)
    return (current - last_successful_retrieval) >= cadence


def refresh_due_sources(*, only: str | None = None, force: bool = False) -> list[dict]:
    results: list[dict] = []
    for source_id, spec in REFRESH_SPECS.items():
        if only and source_id != only:
            continue
        session = SessionLocal()
        try:
            source = session.get(DataSource, source_id)
            last_retrieved = source.last_successful_retrieval if source else None
        finally:
            session.close()
        if not force and not is_due(last_retrieved, spec.cadence):
            results.append({"source": source_id, "status": "skipped_not_due", "last_successful_retrieval": last_retrieved})
            continue
        try:
            with tempfile.TemporaryDirectory(prefix="verifinder-refresh-") as tmp:
                manifest = spec.refresh(Path(tmp))
            results.append({"source": source_id, "status": "refreshed", **manifest})
        except Exception as error:
            results.append({"source": source_id, "status": "failed", "error": str(error)[:500]})

    refreshed_any = any(item["status"] == "refreshed" for item in results)
    if refreshed_any:
        public_session = SessionLocal()
        billing_session = BillingSessionLocal()
        try:
            alerts = scan_for_changes(public_session, billing_session)
            results.append({"source": "watchlist-scan", "status": "scanned", "alerts_created": len(alerts)})
        except Exception as error:
            results.append({"source": "watchlist-scan", "status": "failed", "error": str(error)[:500]})
        finally:
            public_session.close()
            billing_session.close()
    return results
