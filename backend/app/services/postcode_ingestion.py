from __future__ import annotations

import csv
import io
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path

from app.services.dataset_utils import normalise_postcode, sha256_file


class PostcodeSchemaError(ValueError):
    pass


@dataclass(frozen=True)
class PostcodeSnapshot:
    path: Path
    file_hash: str
    record_count: int
    members: tuple[str, ...]


def _data_members(archive: zipfile.ZipFile) -> tuple[str, ...]:
    return tuple(
        sorted(
            name
            for name in archive.namelist()
            if re.search(r"(^|/)Data/CSV/[^/]+\.csv$", name, flags=re.IGNORECASE)
        )
    )


def inspect_postcode_archive(path: Path) -> PostcodeSnapshot:
    if not path.is_file():
        raise FileNotFoundError(path)
    try:
        with zipfile.ZipFile(path) as archive:
            members = _data_members(archive)
            if not members:
                raise PostcodeSchemaError("The Code-Point Open archive has no Data/CSV postcode files.")
            record_count = 0
            for member in members:
                with archive.open(member) as raw:
                    reader = csv.reader(io.TextIOWrapper(raw, encoding="utf-8-sig", newline=""))
                    record_count += sum(1 for row in reader if len(row) >= 10 and row[0].strip())
    except zipfile.BadZipFile as error:
        raise PostcodeSchemaError("The Code-Point Open download is not a valid ZIP archive.") from error
    if record_count == 0:
        raise PostcodeSchemaError("The Code-Point Open archive contains no postcode records.")
    return PostcodeSnapshot(path=path, file_hash=sha256_file(path), record_count=record_count, members=members)


def postcode_rows(snapshot: PostcodeSnapshot, version_id: str):
    with zipfile.ZipFile(snapshot.path) as archive:
        for member in snapshot.members:
            with archive.open(member) as raw:
                reader = csv.reader(io.TextIOWrapper(raw, encoding="utf-8-sig", newline=""))
                for row in reader:
                    if len(row) < 10:
                        continue
                    postcode = row[0].strip()
                    normalised = normalise_postcode(postcode)
                    try:
                        easting = int(row[2])
                        northing = int(row[3])
                    except (TypeError, ValueError):
                        continue
                    if not postcode or not normalised:
                        continue
                    yield {
                        "dataset_version_id": version_id,
                        "postcode": postcode,
                        "normalised_postcode": normalised,
                        "postcode_area": re.match(r"[A-Z]+", normalised).group(0),
                        "positional_quality": int(row[1]) if row[1].strip().isdigit() else None,
                        "easting": easting,
                        "northing": northing,
                        "country_code": row[4].strip() or None,
                        "admin_county_code": row[7].strip() or None,
                        "admin_district_code": row[8].strip() or None,
                        "admin_ward_code": row[9].strip() or None,
                    }
