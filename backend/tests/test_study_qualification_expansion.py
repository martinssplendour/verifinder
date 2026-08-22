from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database import Base
from app.models import (
    DataSource,
    DatasetVersion,
    OfsProviderRecord,
    QualificationExpansionRecord,
    QualificationRecord,
    QualificationUnitMapping,
    QualificationUnitRecord,
    RunStatus,
    SourceHealth,
    StudentSponsorRecord,
)
from app.services.qualification_expansion_ingestion import inspect_welsh_qualifications, welsh_qualification_rows
from app.services.qualification_lookup import get_qualification, search_qualifications
from app.services.study_lookup import get_study_provider, search_study_providers


def _source(source_id: str, name: str) -> DataSource:
    return DataSource(
        id=source_id,
        organisation=name,
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


def expanded_session() -> Session:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = Session(engine)
    sources = [
        _source("home-office-student-sponsors", "UK Visas and Immigration"),
        _source("office-for-students-register", "Office for Students"),
        _source("ofqual-register", "Ofqual"),
        _source("qualifications-wales-qiw", "Qualifications Wales"),
        _source("ofqual-qualification-units", "Ofqual units"),
    ]
    versions = [
        _version("home-office-student-sponsors", "student-version", "a"),
        _version("office-for-students-register", "ofs-version", "b"),
        _version("ofqual-register", "ofqual-version", "c"),
        _version("qualifications-wales-qiw", "qiw-version", "d"),
        _version("ofqual-qualification-units", "unit-version", "e"),
    ]
    student = StudentSponsorRecord(
        dataset_version_id="student-version",
        source_record_key="student-key",
        organisation_name="Example University",
        normalised_name="example university",
        town_city="Cardiff",
        sponsor_type="Higher Education Institution (HEI)",
        status="Student Sponsor - Track Record",
        routes=["Student"],
    )
    ofs = OfsProviderRecord(
        dataset_version_id="ofs-version",
        ukprn="10000001",
        legal_name="Example University",
        normalised_name="example university",
        trading_names=[],
        normalised_aliases="example university",
        registration_category="Approved (fee cap)",
    )
    ofqual = QualificationRecord(
        id="ofqual-record",
        dataset_version_id="ofqual-version",
        qualification_number="ABC/123/4",
        normalised_number="abc1234",
        title="Example Accounting Diploma",
        normalised_title="example accounting diploma",
        awarding_organisation_number="RN100",
        awarding_organisation_name="Example Awards",
        level="Level 3",
        status="Available to learners",
        raw_record={},
    )
    qiw = QualificationExpansionRecord(
        dataset_version_id="qiw-version",
        source_record_key="C00/1234/5",
        regulator="Qualifications Wales",
        jurisdiction="Wales",
        qualification_number="DEF/456/7",
        normalised_number="def4567",
        approval_number="C00/1234/5",
        title="Example Accounting Certificate",
        normalised_title="example accounting certificate",
        awarding_organisation_name="Welsh Awards",
        normalised_organisation_name="welsh awards",
        status="Available to learners",
        languages=["English", "Welsh"],
    )
    unit = QualificationUnitRecord(
        dataset_version_id="unit-version",
        unit_key="unit-1",
        unit_reference="A/100/0001",
        title="Accounting Fundamentals",
        normalised_title="accounting fundamentals",
        level="Level 3",
        credit_value=4,
        guided_learning_hours=20,
    )
    mapping = QualificationUnitMapping(
        dataset_version_id="unit-version",
        qualification_number="ABC/123/4",
        normalised_qualification_number="abc1234",
        unit_key="unit-1",
    )
    session.add_all([*sources, *versions, student, ofs, ofqual, qiw, unit, mapping])
    session.commit()
    return session


def test_study_search_keeps_registers_separate_and_cross_links_exact_name():
    session = expanded_session()
    results, student_context, ofs_context = search_study_providers(session, "Example University")
    assert student_context is not None and ofs_context is not None
    assert {result.record_type for result in results} == {"student_sponsor", "ofs"}
    student = next(result for result in results if result.record_type == "student_sponsor")
    detail = get_study_provider(session, "student_sponsor", int(student.id))
    assert detail is not None
    assert detail.matched_record is not None
    assert detail.matched_record.ukprn == "10000001"


def test_qualification_search_covers_wales_and_ofqual_detail_includes_units():
    session = expanded_session()
    results, context = search_qualifications(session, "Example Accounting")
    assert context is not None
    assert {result.record_type for result in results} == {"ofqual", "qiw"}
    detail = get_qualification(session, "ofqual-record")
    assert detail is not None
    assert detail.unit_count == 1
    assert detail.units[0].title == "Accounting Fundamentals"
    welsh = next(result for result in results if result.record_type == "qiw")
    welsh_detail = get_qualification(session, welsh.id)
    assert welsh_detail is not None
    assert welsh_detail.jurisdiction == "Wales"
    assert welsh_detail.languages == ["English", "Welsh"]


def test_welsh_ingestion_deduplicates_repeated_approval_rows(tmp_path: Path):
    source = tmp_path / "qiw.csv"
    source.write_text(
        "QW Approval/Designation No.,Awarding Body,English qualification title,Qualification number,Status\n"
        "C00/0001/1,Example Awards,Example Diploma,100/0001/1,Available to learners\n"
        "C00/0001/1,Example Awards,Example Diploma,100/0001/1,Available to learners\n",
        encoding="utf-8",
    )
    snapshot = inspect_welsh_qualifications(source)
    assert len(list(welsh_qualification_rows(snapshot, "version"))) == 1
