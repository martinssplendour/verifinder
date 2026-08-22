from pathlib import Path

from app.services.food_ingestion import food_rows, inspect_food_file
from app.services.qualification_ingestion import (
    inspect_qualification_files,
    organisation_rows,
    qualification_rows,
)


def test_ofqual_files_are_validated_and_mapped(tmp_path: Path):
    qualifications = tmp_path / "qualifications.csv"
    organisations = tmp_path / "organisations.csv"
    qualifications.write_text(
        "Qualification Number,Qualification Title,Owner Organisation Recognition Number,Owner Organisation Name,Qualification Status,Qualification Level,Offered In England\n"
        "ABC/123/4,Example Level 4 Diploma,RN100,Example Awards,Available to learners,Level 4,Yes\n",
        encoding="utf-8",
    )
    organisations.write_text(
        "Recognition Number,Name,Ofqual Status,Website\nRN100,Example Awards,Recognised,https://example.test\n",
        encoding="utf-8",
    )
    snapshot = inspect_qualification_files(qualifications, organisations)
    qualification = next(qualification_rows(snapshot, "version-1"))
    organisation = next(organisation_rows(snapshot, "version-1"))
    assert snapshot.qualification_count == 1
    assert qualification["normalised_number"] == "abc1234"
    assert qualification["offered_in_england"] is True
    assert organisation["recognition_number"] == "RN100"


def test_food_file_uses_the_bulk_download_column_names(tmp_path: Path):
    source = tmp_path / "food.csv"
    source.write_text(
        "AddressLine1,BusinessType,FHRSID,BusinessName,ConfidenceInManagement,Hygiene,Latitude,LocalAuthorityName,Longitude,NewRatingPending,PostCode,RatingDate,RatingKey,RatingValue,SchemeType,Structural\n"
        "1 High Street,Restaurant/Cafe/Canteen,123,Example Cafe,5,0,51.5,Example Council,-0.1,False,AB1 2CD,2026-08-20,fhrs_5_en-GB,5,FHRS,5\n",
        encoding="utf-8",
    )
    snapshot = inspect_food_file(source)
    record = next(food_rows(snapshot, "version-1"))
    assert snapshot.record_count == 1
    assert record["normalised_postcode"] == "AB12CD"
    assert record["hygiene_score"] == 0
    assert record["structural_score"] == 5
    assert record["confidence_in_management_score"] == 5
