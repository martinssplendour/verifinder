from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass
from pathlib import Path

from app.services.dataset_utils import combined_sha256, normalise_postcode, parse_date
from app.services.normalization import normalise_name


class PropertySchemaError(ValueError):
    pass


@dataclass(frozen=True)
class PropertySnapshot:
    paths: tuple[Path, ...]
    file_hash: str
    record_count: int


def inspect_property_files(paths: list[Path] | tuple[Path, ...]) -> PropertySnapshot:
    unique_paths = tuple(dict.fromkeys(path.resolve() for path in paths))
    if not unique_paths:
        raise PropertySchemaError("At least one HM Land Registry Price Paid CSV is required.")
    record_count = 0
    for path in unique_paths:
        if not path.is_file():
            raise FileNotFoundError(path)
        with path.open("r", encoding="utf-8-sig", newline="") as source:
            reader = csv.reader(source)
            for row in reader:
                if row and len(row) != 16:
                    raise PropertySchemaError(f"{path.name} contains a row with {len(row)} columns; expected 16.")
                record_count += int(bool(row))
    if record_count == 0:
        raise PropertySchemaError("The Price Paid files contain no sale records.")
    return PropertySnapshot(paths=unique_paths, file_hash=combined_sha256(unique_paths), record_count=record_count)


def _address(parts: list[str]) -> str:
    result: list[str] = []
    seen: set[str] = set()
    for raw in parts:
        value = raw.strip()
        key = normalise_name(value)
        if value and key and key not in seen:
            result.append(value)
            seen.add(key)
    return ", ".join(result)


def _property_key(postcode: str | None, saon: str, paon: str, street: str, town_city: str) -> str:
    identity = "|".join(
        (normalise_postcode(postcode) or "", normalise_name(saon), normalise_name(paon), normalise_name(street), normalise_name(town_city))
    )
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()[:32]


def property_rows(snapshot: PropertySnapshot, version_id: str):
    for path in snapshot.paths:
        with path.open("r", encoding="utf-8-sig", newline="") as source:
            for row in csv.reader(source):
                if len(row) != 16:
                    continue
                transaction_id, price_raw, transferred_raw, postcode = (value.strip() for value in row[:4])
                transfer_date = parse_date(transferred_raw)
                try:
                    price = int(price_raw)
                except ValueError:
                    continue
                if not transaction_id or transfer_date is None or row[15].strip().upper() == "D":
                    continue
                property_type, old_new, tenure = (value.strip().upper() for value in row[4:7])
                paon, saon, street, locality, town_city, district, county = (value.strip() for value in row[7:14])
                full_address = _address([saon, paon, street, locality, town_city, district, county, postcode])
                yield {
                    "dataset_version_id": version_id,
                    "transaction_id": transaction_id.strip("{}"),
                    "price": price,
                    "transfer_date": transfer_date,
                    "postcode": postcode or None,
                    "normalised_postcode": normalise_postcode(postcode),
                    "property_type": property_type or None,
                    "new_build": old_new == "Y" if old_new in {"Y", "N"} else None,
                    "tenure": tenure or None,
                    "paon": paon or None,
                    "saon": saon or None,
                    "street": street or None,
                    "locality": locality or None,
                    "town_city": town_city or None,
                    "district": district or None,
                    "county": county or None,
                    "full_address": full_address,
                    "normalised_address": normalise_name(full_address),
                    "property_key": _property_key(postcode, saon, paon, street, town_city),
                    "ppd_category": row[14].strip().upper() or None,
                    "record_status": row[15].strip().upper() or None,
                }
