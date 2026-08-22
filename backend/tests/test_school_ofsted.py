import csv
from datetime import date, datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database import Base
from app.models import DataSource, DatasetVersion, OfstedInspectionRecord, RunStatus, SchoolRecord, SourceHealth
from app.services.gias_ingestion import GiasSchemaError, _parse_gias_date, gias_rows, inspect_gias_file
from app.services.ofsted_ingestion import (
    OfstedSchemaError,
    _clean,
    _parse_ofsted_bool,
    _parse_ofsted_date,
    inspect_ofsted_file,
    ofsted_rows,
)
from app.services.school_lookup import get_school, search_schools


def test_parse_gias_date_reads_day_month_year():
    assert _parse_gias_date("01-09-2015") == date(2015, 9, 1)
    assert _parse_gias_date("") is None
    assert _parse_gias_date(None) is None


def test_parse_ofsted_date_reads_slash_format():
    assert _parse_ofsted_date("13/01/2026") == date(2026, 1, 13)
    assert _parse_ofsted_date("NULL") is None


def test_parse_ofsted_bool_and_clean_treat_null_literal_as_blank():
    assert _parse_ofsted_bool("Yes") is True
    assert _parse_ofsted_bool("No") is False
    assert _parse_ofsted_bool("NULL") is None
    assert _clean("NULL") is None
    assert _clean("  Met ") == "Met"


def _write_gias_csv(path: Path) -> Path:
    file_path = path / "gias.csv"
    with file_path.open("w", encoding="cp1252", newline="") as target:
        writer = csv.writer(target)
        writer.writerow([
            "URN", "LA (name)", "EstablishmentName", "TypeOfEstablishment (name)",
            "EstablishmentTypeGroup (name)", "EstablishmentStatus (name)", "PhaseOfEducation (name)",
            "StatutoryLowAge", "StatutoryHighAge", "Gender (name)", "ReligiousCharacter (name)",
            "SchoolCapacity", "NumberOfPupils", "UKPRN", "OpenDate", "CloseDate", "Street", "Locality",
            "Town", "County (name)", "Postcode", "SchoolWebsite", "TelephoneNum", "HeadFirstName",
            "HeadLastName", "GOR (name)", "Country (name)",
        ])
        writer.writerow([
            "100000", "Camden", "Gospel Oak Primary School", "Community School", "Local authority maintained schools",
            "Open", "Primary", "3", "11", "Mixed", "Does not apply", "450", "421", "10012345",
            "01-09-1990", "", "1 Example Road", "", "London", "Greater London", "NW3 2JB",
            "www.example.test", "02071234567", "Jane", "Smith", "London", "England",
        ])
    return file_path


def _write_ofsted_csv(path: Path) -> Path:
    file_path = path / "ofsted.csv"
    with file_path.open("w", encoding="cp1252", newline="") as target:
        writer = csv.writer(target)
        writer.writerow([
            "URN", "School name", "Ofsted phase", "Local authority", "Region", "Postcode",
            "Most recent category of concern", "Inspection number of latest full inspection", "Inspection type",
            "Inspection start date", "Publication date", "Safeguarding standards", "Inclusion",
            "Curriculum and teaching", "Achievement", "Attendance and behaviour",
            "Personal development and wellbeing", "Early years (where applicable)",
            "Post-16 provision (where applicable)", "Leadership and governance",
            "Inspection start date of latest OEIF graded inspection",
            "Publication date of latest OEIF graded inspection", "Latest OEIF overall effectiveness",
            "Latest OEIF  safeguarding is effective?", "Date of latest ungraded inspection",
            "Ungraded inspection publication date", "Ungraded inspection overall outcome",
        ])
        writer.writerow([
            "100000", "Gospel Oak Primary School", "Primary", "Camden", "London", "NW3 2JB", "NULL",
            "10428056", "S5 Inspection", "13/01/2026", "09/02/2026", "Met", "Strong standard",
            "Strong standard", "Strong standard", "Expected standard", "Strong standard",
            "Strong standard", "Not applicable", "Strong standard", "NULL", "NULL", "NULL", "NULL",
            "20/10/2021", "25/11/2021", "School remains Outstanding",
        ])
    return file_path


def test_gias_file_missing_urn_column_is_rejected(tmp_path: Path):
    path = tmp_path / "gias-no-urn.csv"
    path.write_text("EstablishmentName\nExample School\n", encoding="cp1252")
    with pytest.raises(GiasSchemaError, match="URN"):
        inspect_gias_file(path)


def test_gias_file_without_usable_rows_is_rejected(tmp_path: Path):
    path = tmp_path / "gias-empty.csv"
    path.write_text("URN,EstablishmentName\n,\n", encoding="cp1252")
    with pytest.raises(GiasSchemaError, match="no establishment records"):
        inspect_gias_file(path)


def test_ofsted_file_missing_urn_column_is_rejected(tmp_path: Path):
    path = tmp_path / "ofsted-no-urn.csv"
    path.write_text("School name\nExample School\n", encoding="cp1252")
    with pytest.raises(OfstedSchemaError, match="URN"):
        inspect_ofsted_file(path)


def test_ofsted_file_without_usable_rows_is_rejected(tmp_path: Path):
    path = tmp_path / "ofsted-empty.csv"
    path.write_text("URN,School name\n,\n", encoding="cp1252")
    with pytest.raises(OfstedSchemaError, match="no inspection records"):
        inspect_ofsted_file(path)


def test_gias_rows_maps_real_column_names(tmp_path: Path):
    path = _write_gias_csv(tmp_path)
    snapshot = inspect_gias_file(path)
    assert snapshot.record_count == 1
    record = next(gias_rows(snapshot, "version-1"))
    assert record["urn"] == "100000"
    assert record["establishment_name"] == "Gospel Oak Primary School"
    assert record["normalised_postcode"] == "NW32JB"
    assert record["open_date"] == date(1990, 9, 1)
    assert record["close_date"] is None
    assert record["number_of_pupils"] == 421


def test_ofsted_rows_maps_real_column_names(tmp_path: Path):
    path = _write_ofsted_csv(tmp_path)
    snapshot = inspect_ofsted_file(path)
    assert snapshot.record_count == 1
    record = next(ofsted_rows(snapshot, "version-1"))
    assert record["urn"] == "100000"
    assert record["safeguarding_standards"] == "Met"
    assert record["achievement"] == "Strong standard"
    assert record["full_inspection_start_date"] == date(2026, 1, 13)
    assert record["oeif_overall_effectiveness"] is None
    assert record["ungraded_overall_outcome"] == "School remains Outstanding"
    assert record["most_recent_category_of_concern"] is None


def _source(source_id: str, organisation: str, name: str) -> DataSource:
    return DataSource(
        id=source_id,
        organisation=organisation,
        name=name,
        source_type="CSV",
        official_url="https://example.test",
        country="GB",
        health=SourceHealth.HEALTHY,
    )


def _version(source_id: str, version_id: str, hash_character: str) -> DatasetVersion:
    retrieved = datetime(2026, 8, 22, tzinfo=timezone.utc)
    return DatasetVersion(
        id=version_id,
        source_id=source_id,
        version_identifier=f"2026-08-22-{version_id}",
        retrieved_at=retrieved,
        file_hash=hash_character * 64,
        record_count=1,
        storage_location="fixture",
        processing_status=RunStatus.SUCCEEDED,
    )


def _school_session() -> Session:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = Session(engine)
    school_source = _source("gias-establishments", "Department for Education", "GIAS")
    ofsted_source = _source("ofsted-school-inspections", "Ofsted", "Ofsted inspections")
    school_version = _version("gias-establishments", "school-version", "1")
    ofsted_version = _version("ofsted-school-inspections", "ofsted-version", "2")
    school = SchoolRecord(
        dataset_version_id=school_version.id,
        urn="100000",
        establishment_name="Gospel Oak Primary School",
        normalised_name="gospel oak primary school",
        la_name="Camden",
        type_name="Community School",
        status_name="Open",
        phase_name="Primary",
        postcode="NW3 2JB",
        normalised_postcode="NW32JB",
        town="London",
        raw_record={},
    )
    inspection = OfstedInspectionRecord(
        dataset_version_id=ofsted_version.id,
        urn="100000",
        school_name="Gospel Oak Primary School",
        safeguarding_standards="Met",
        achievement="Strong standard",
        full_inspection_start_date=date(2026, 1, 13),
        raw_record={},
    )
    session.add_all([school_source, ofsted_source, school_version, ofsted_version, school, inspection])
    session.commit()
    return session


def test_search_and_get_school_attaches_matching_ofsted_inspection():
    session = _school_session()
    results, context = search_schools(session, "Gospel Oak")
    assert context is not None
    assert results[0].urn == "100000"

    detail = get_school(session, "100000")
    assert detail is not None
    assert detail.ofsted.status == "matched"
    assert detail.ofsted.safeguarding_standards == "Met"
    assert detail.ofsted.achievement == "Strong standard"


def test_get_school_without_matching_urn_reports_data_unavailable():
    session = _school_session()
    session.execute(OfstedInspectionRecord.__table__.delete())
    session.commit()

    detail = get_school(session, "100000")
    assert detail is not None
    assert detail.ofsted.status == "data_unavailable"
    assert "No matching URN" in (detail.ofsted.message or "")


def test_get_school_returns_none_for_unknown_urn():
    session = _school_session()
    assert get_school(session, "999999") is None


def test_search_schools_matches_by_exact_urn():
    session = _school_session()
    results, context = search_schools(session, "100000")
    assert context is not None
    assert results[0].urn == "100000"
    assert results[0].establishment_name == "Gospel Oak Primary School"
