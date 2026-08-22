from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from app.services.dataset_utils import (
    count_csv_rows,
    csv_header,
    csv_rows,
    normalise_postcode,
    parse_bool,
    parse_date,
    parse_float,
    parse_int,
    sha256_file,
)
from app.services.normalization import normalise_name


class FoodSchemaError(ValueError):
    pass


@dataclass(frozen=True)
class FoodSnapshot:
    path: Path
    file_hash: str
    record_count: int
    columns: dict[str, str]


def _key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def inspect_food_file(path: Path) -> FoodSnapshot:
    if not path.is_file():
        raise FileNotFoundError(path)
    columns = {_key(column): column for column in csv_header(path)}
    missing = sorted(name for name in ("fhrsid", "businessname", "ratingvalue") if name not in columns)
    if missing:
        raise FoodSchemaError(f"Missing required food hygiene columns: {missing}")
    record_count = count_csv_rows(path)
    if record_count == 0:
        raise FoodSchemaError("The food hygiene file contains no establishment records.")
    return FoodSnapshot(path=path, file_hash=sha256_file(path), record_count=record_count, columns=columns)


def food_rows(snapshot: FoodSnapshot, version_id: str):
    columns = snapshot.columns

    def value(row: dict[str, str], *aliases: str) -> str:
        column = next((columns.get(_key(alias)) for alias in aliases if columns.get(_key(alias))), None)
        return (row.get(column, "") if column else "").strip()

    for row in csv_rows(snapshot.path):
        fhrs_id = value(row, "FHRSID")
        business_name = value(row, "BusinessName")
        if not fhrs_id or not business_name:
            continue
        address_parts = [value(row, f"AddressLine{index}") for index in range(1, 5)]
        address = ", ".join(part for part in address_parts if part) or None
        postcode = value(row, "PostCode") or None
        yield {
            "dataset_version_id": version_id,
            "fhrs_id": fhrs_id,
            "local_authority_business_id": value(row, "LocalAuthorityBusinessID") or None,
            "business_name": business_name,
            "normalised_name": normalise_name(business_name),
            "business_type": value(row, "BusinessType") or None,
            "address": address,
            "postcode": postcode,
            "normalised_postcode": normalise_postcode(postcode),
            "rating_value": value(row, "RatingValue") or None,
            "rating_key": value(row, "RatingKey") or None,
            "rating_date": parse_date(value(row, "RatingDate")),
            "local_authority_code": value(row, "LocalAuthorityCode") or None,
            "local_authority_name": value(row, "LocalAuthorityName") or None,
            "scheme_type": value(row, "SchemeType") or None,
            "new_rating_pending": parse_bool(value(row, "NewRatingPending")),
            "hygiene_score": parse_int(value(row, "Scores_Hygiene", "Scores Hygiene", "Hygiene")),
            "structural_score": parse_int(value(row, "Scores_Structural", "Scores Structural", "Structural")),
            "confidence_in_management_score": parse_int(
                value(
                    row,
                    "Scores_ConfidenceInManagement",
                    "Scores ConfidenceInManagement",
                    "ConfidenceInManagement",
                )
            ),
            "longitude": parse_float(value(row, "Geocode_Longitude", "Longitude")),
            "latitude": parse_float(value(row, "Geocode_Latitude", "Latitude")),
            "raw_record": {},
        }
