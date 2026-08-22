from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database import Base
from app.models import (
    DataSource,
    DatasetVersion,
    FoodEstablishmentRecord,
    QualificationRecord,
    RunStatus,
    SourceHealth,
)
from app.services.food_lookup import get_food_establishment, search_food_establishments
from app.services.qualification_lookup import get_qualification, search_qualifications


def public_data_session() -> Session:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = Session(engine)
    retrieved = datetime(2026, 8, 21, tzinfo=timezone.utc)
    ofqual = DataSource(
        id="ofqual-register",
        organisation="Ofqual",
        name="Register of Regulated Qualifications",
        source_type="CSV",
        official_url="https://www.gov.uk/find-a-regulated-qualification",
        country="GB",
        health=SourceHealth.HEALTHY,
        last_successful_retrieval=retrieved,
    )
    food = DataSource(
        id="fsa-food-hygiene",
        organisation="Food Standards Agency",
        name="Food Hygiene Rating Scheme open data",
        source_type="CSV",
        official_url="https://ratings.food.gov.uk/open-data",
        country="GB",
        health=SourceHealth.HEALTHY,
        last_successful_retrieval=retrieved,
    )
    qualification_version = DatasetVersion(
        id="qualification-version",
        source_id=ofqual.id,
        version_identifier="2026-08-21-qualifications",
        retrieved_at=retrieved,
        published_at=retrieved,
        file_hash="d" * 64,
        record_count=1,
        storage_location="qualifications.csv",
        processing_status=RunStatus.SUCCEEDED,
    )
    food_version = DatasetVersion(
        id="food-version",
        source_id=food.id,
        version_identifier="2026-08-21-food",
        retrieved_at=retrieved,
        published_at=retrieved,
        file_hash="e" * 64,
        record_count=1,
        storage_location="food.csv",
        processing_status=RunStatus.SUCCEEDED,
    )
    qualification = QualificationRecord(
        dataset_version_id=qualification_version.id,
        qualification_number="ABC/123/4",
        normalised_number="abc1234",
        title="Example Level 4 Diploma",
        normalised_title="example level 4 diploma",
        awarding_organisation_number="RN100",
        awarding_organisation_name="Example Awards",
        level="Level 4",
        status="Available to learners",
        raw_record={},
    )
    establishment = FoodEstablishmentRecord(
        dataset_version_id=food_version.id,
        fhrs_id="123",
        business_name="Example Cafe",
        normalised_name="example cafe",
        postcode="AB1 2CD",
        normalised_postcode="AB12CD",
        rating_value="5",
        local_authority_name="Example Council",
        raw_record={},
    )
    session.add_all([ofqual, food, qualification_version, food_version, qualification, establishment])
    session.commit()
    return session


def test_qualification_search_and_detail_include_provenance():
    session = public_data_session()
    results, context = search_qualifications(session, "ABC/123/4")
    assert context is not None
    assert results[0].title == "Example Level 4 Diploma"
    detail = get_qualification(session, results[0].id)
    assert detail is not None
    assert detail.source.organisation == "Ofqual"


def test_food_search_by_postcode_and_detail_include_rating():
    session = public_data_session()
    results, context = search_food_establishments(session, "AB1 2CD")
    assert context is not None
    assert results[0].business_name == "Example Cafe"
    detail = get_food_establishment(session, results[0].id)
    assert detail is not None
    assert detail.rating_value == "5"
