import argparse
import json
import shutil
from datetime import date, datetime, timezone
from pathlib import Path

from app.config import get_settings
from app.services.dataset_utils import sha256_file
from app.services.food_ingestion import FoodSchemaError, inspect_food_file
from app.services.food_loader import load_food_snapshot
from app.services.gias_ingestion import GiasSchemaError, inspect_gias_file
from app.services.gias_loader import load_gias_snapshot
from app.services.ofsted_ingestion import OfstedSchemaError, inspect_ofsted_file
from app.services.ofsted_loader import load_ofsted_snapshot
from app.services.postcode_ingestion import PostcodeSchemaError, inspect_postcode_archive
from app.services.postcode_loader import load_postcode_snapshot
from app.services.property_ingestion import PropertySchemaError, inspect_property_files
from app.services.property_loader import load_property_snapshot
from app.services.qualification_ingestion import QualificationSchemaError, inspect_qualification_files
from app.services.qualification_loader import load_qualification_snapshot
from app.services.qualification_expansion_ingestion import (
    QualificationExpansionSchemaError,
    inspect_welsh_qualifications,
)
from app.services.qualification_expansion_loader import load_welsh_qualifications
from app.services.qualification_unit_ingestion import QualificationUnitSchemaError, inspect_qualification_unit_files
from app.services.qualification_unit_loader import load_qualification_units
from app.services.sponsor_ingestion import SponsorSchemaError, read_snapshot
from app.services.sponsor_loader import load_snapshot
from app.services.study_ingestion import StudySchemaError, inspect_ofs_register, inspect_student_sponsors
from app.services.study_loader import load_ofs_register, load_student_sponsors


def ingest_sponsor_file(source_file: Path, published_on: date | None = None) -> dict:
    settings = get_settings()
    snapshot = read_snapshot(source_file)
    retrieved_at = datetime.now(timezone.utc)
    destination_dir = Path(settings.raw_data_storage) / "home-office" / "worker-sponsors"
    destination_dir.mkdir(parents=True, exist_ok=True)
    if source_file.resolve().parent == destination_dir.resolve():
        destination = source_file.resolve()
    else:
        destination = destination_dir / f"{retrieved_at:%Y%m%dT%H%M%SZ}-{snapshot.file_hash[:12]}.csv"
    if not destination.exists():
        shutil.copy2(source_file, destination)
    load_result = load_snapshot(snapshot, destination, retrieved_at, published_on)
    manifest = {
        "source": "home-office-worker-sponsors",
        "retrieved_at": retrieved_at.isoformat(),
        "file_hash": snapshot.file_hash,
        "record_count": len(snapshot.records),
        "storage_location": str(destination),
        "published_at": published_on.isoformat() if published_on else None,
        **load_result,
    }
    manifest_path = destination.with_suffix(".json")
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def _preserve(source_file: Path, destination_dir: Path, filename: str) -> Path:
    destination_dir.mkdir(parents=True, exist_ok=True)
    if source_file.resolve().parent == destination_dir.resolve():
        return source_file.resolve()
    destination = destination_dir / filename
    if not destination.exists():
        shutil.copy2(source_file, destination)
    return destination


def ingest_qualification_files(
    qualifications_file: Path,
    organisations_file: Path,
    published_on: date | None = None,
) -> dict:
    settings = get_settings()
    retrieved_at = datetime.now(timezone.utc)
    destination_dir = Path(settings.raw_data_storage) / "ofqual"
    qualification_hash = sha256_file(qualifications_file)
    organisation_hash = sha256_file(organisations_file)
    qualifications = _preserve(
        qualifications_file,
        destination_dir,
        f"{retrieved_at:%Y%m%dT%H%M%SZ}-qualifications-{qualification_hash[:12]}.csv",
    )
    organisations = _preserve(
        organisations_file,
        destination_dir,
        f"{retrieved_at:%Y%m%dT%H%M%SZ}-organisations-{organisation_hash[:12]}.csv",
    )
    snapshot = inspect_qualification_files(qualifications, organisations)
    result = load_qualification_snapshot(snapshot, retrieved_at, published_on)
    manifest = {
        "source": "ofqual-register",
        "retrieved_at": retrieved_at.isoformat(),
        "published_at": published_on.isoformat() if published_on else None,
        "file_hash": snapshot.file_hash,
        "qualification_count": snapshot.qualification_count,
        "organisation_count": snapshot.organisation_count,
        "storage_locations": {"qualifications": str(qualifications), "organisations": str(organisations)},
        **result,
    }
    manifest_path = qualifications.with_suffix(".json")
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def ingest_food_file(source_file: Path, published_on: date | None = None) -> dict:
    settings = get_settings()
    retrieved_at = datetime.now(timezone.utc)
    file_hash = sha256_file(source_file)
    destination_dir = Path(settings.raw_data_storage) / "food-standards-agency" / "food-hygiene"
    destination = _preserve(
        source_file,
        destination_dir,
        f"{retrieved_at:%Y%m%dT%H%M%SZ}-fhrs-{file_hash[:12]}.csv",
    )
    snapshot = inspect_food_file(destination)
    result = load_food_snapshot(snapshot, retrieved_at, published_on)
    manifest = {
        "source": "fsa-food-hygiene",
        "retrieved_at": retrieved_at.isoformat(),
        "published_at": published_on.isoformat() if published_on else None,
        "file_hash": snapshot.file_hash,
        "record_count": snapshot.record_count,
        "storage_location": str(destination),
        **result,
    }
    destination.with_suffix(".json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def ingest_postcode_file(source_file: Path, published_on: date | None = None) -> dict:
    settings = get_settings()
    retrieved_at = datetime.now(timezone.utc)
    file_hash = sha256_file(source_file)
    destination_dir = Path(settings.raw_data_storage) / "ordnance-survey" / "code-point-open"
    destination = _preserve(source_file, destination_dir, f"{retrieved_at:%Y%m%dT%H%M%SZ}-code-point-{file_hash[:12]}.zip")
    snapshot = inspect_postcode_archive(destination)
    result = load_postcode_snapshot(snapshot, retrieved_at, published_on)
    manifest = {
        "source": "os-code-point-open",
        "retrieved_at": retrieved_at.isoformat(),
        "published_at": published_on.isoformat() if published_on else None,
        "file_hash": snapshot.file_hash,
        "record_count": snapshot.record_count,
        "storage_location": str(destination),
        **result,
    }
    destination.with_suffix(".json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def ingest_property_files(source_files: list[Path], published_on: date | None = None) -> dict:
    settings = get_settings()
    retrieved_at = datetime.now(timezone.utc)
    destination_dir = Path(settings.raw_data_storage) / "hm-land-registry" / "price-paid"
    preserved = [
        _preserve(source_file, destination_dir, f"{retrieved_at:%Y%m%dT%H%M%SZ}-{source_file.name}")
        for source_file in source_files
    ]
    snapshot = inspect_property_files(preserved)
    result = load_property_snapshot(snapshot, retrieved_at, published_on)
    manifest = {
        "source": "hm-land-registry-price-paid",
        "retrieved_at": retrieved_at.isoformat(),
        "published_at": published_on.isoformat() if published_on else None,
        "file_hash": snapshot.file_hash,
        "record_count": snapshot.record_count,
        "storage_locations": [str(path) for path in preserved],
        **result,
    }
    preserved[0].with_suffix(".json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def ingest_study_provider_files(student_file: Path, ofs_file: Path, published_on: date | None = None) -> dict:
    settings = get_settings()
    retrieved_at = datetime.now(timezone.utc)
    student_dir = Path(settings.raw_data_storage) / "home-office" / "student-sponsors"
    ofs_dir = Path(settings.raw_data_storage) / "office-for-students" / "register"
    student = _preserve(student_file, student_dir, f"{retrieved_at:%Y%m%dT%H%M%SZ}-student-sponsors.csv")
    ofs = _preserve(ofs_file, ofs_dir, f"{retrieved_at:%Y%m%dT%H%M%SZ}-ofs-register.xlsx")
    student_snapshot = inspect_student_sponsors(student)
    ofs_snapshot = inspect_ofs_register(ofs)
    student_result = load_student_sponsors(student_snapshot, retrieved_at, published_on)
    ofs_result = load_ofs_register(ofs_snapshot, retrieved_at, published_on)
    manifest = {
        "source": "study-providers",
        "retrieved_at": retrieved_at.isoformat(),
        "published_at": published_on.isoformat() if published_on else None,
        "student_sponsors": {"storage_location": str(student), **student_result},
        "ofs_register": {"storage_location": str(ofs), **ofs_result},
    }
    student.with_suffix(".json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def ingest_qualification_unit_files(units_file: Path, mappings_file: Path, published_on: date | None = None) -> dict:
    settings = get_settings()
    retrieved_at = datetime.now(timezone.utc)
    destination_dir = Path(settings.raw_data_storage) / "ofqual" / "expansion"
    units = _preserve(units_file, destination_dir, f"{retrieved_at:%Y%m%dT%H%M%SZ}-units.csv")
    mappings = _preserve(mappings_file, destination_dir, f"{retrieved_at:%Y%m%dT%H%M%SZ}-qualification-units.csv")
    snapshot = inspect_qualification_unit_files(units, mappings)
    result = load_qualification_units(snapshot, retrieved_at, published_on)
    manifest = {
        "source": "ofqual-qualification-units",
        "retrieved_at": retrieved_at.isoformat(),
        "published_at": published_on.isoformat() if published_on else None,
        "storage_locations": {"units": str(units), "mappings": str(mappings)},
        "unit_count": snapshot.unit_count,
        "mapping_count": snapshot.mapping_count,
        **result,
    }
    units.with_suffix(".json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def ingest_welsh_qualification_file(source_file: Path, published_on: date | None = None) -> dict:
    settings = get_settings()
    retrieved_at = datetime.now(timezone.utc)
    destination_dir = Path(settings.raw_data_storage) / "qualifications-wales"
    destination = _preserve(source_file, destination_dir, f"{retrieved_at:%Y%m%dT%H%M%SZ}-qiw-complete-en.csv")
    snapshot = inspect_welsh_qualifications(destination)
    result = load_welsh_qualifications(snapshot, retrieved_at, published_on)
    manifest = {
        "source": "qualifications-wales-qiw",
        "retrieved_at": retrieved_at.isoformat(),
        "published_at": published_on.isoformat() if published_on else None,
        "storage_location": str(destination),
        **result,
    }
    destination.with_suffix(".json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def ingest_school_file(source_file: Path, published_on: date | None = None) -> dict:
    settings = get_settings()
    retrieved_at = datetime.now(timezone.utc)
    file_hash = sha256_file(source_file)
    destination_dir = Path(settings.raw_data_storage) / "department-for-education" / "gias"
    destination = _preserve(source_file, destination_dir, f"{retrieved_at:%Y%m%dT%H%M%SZ}-edubasealldata-{file_hash[:12]}.csv")
    snapshot = inspect_gias_file(destination)
    result = load_gias_snapshot(snapshot, retrieved_at, published_on)
    manifest = {
        "source": "gias-establishments",
        "retrieved_at": retrieved_at.isoformat(),
        "published_at": published_on.isoformat() if published_on else None,
        "file_hash": snapshot.file_hash,
        "record_count": snapshot.record_count,
        "storage_location": str(destination),
        **result,
    }
    destination.with_suffix(".json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def ingest_ofsted_file(source_file: Path, published_on: date | None = None) -> dict:
    settings = get_settings()
    retrieved_at = datetime.now(timezone.utc)
    file_hash = sha256_file(source_file)
    destination_dir = Path(settings.raw_data_storage) / "ofsted" / "inspections"
    destination = _preserve(source_file, destination_dir, f"{retrieved_at:%Y%m%dT%H%M%SZ}-latest-inspections-{file_hash[:12]}.csv")
    snapshot = inspect_ofsted_file(destination)
    result = load_ofsted_snapshot(snapshot, retrieved_at, published_on)
    manifest = {
        "source": "ofsted-school-inspections",
        "retrieved_at": retrieved_at.isoformat(),
        "published_at": published_on.isoformat() if published_on else None,
        "file_hash": snapshot.file_hash,
        "record_count": snapshot.record_count,
        "storage_location": str(destination),
        **result,
    }
    destination.with_suffix(".json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="VeriFinder data pipeline commands")
    subparsers = parser.add_subparsers(dest="command", required=True)
    ingest = subparsers.add_parser("ingest-sponsors", help="Validate and preserve an official sponsor CSV")
    ingest.add_argument("file", type=Path)
    ingest.add_argument("--published-at", type=date.fromisoformat, help="Official publication date (YYYY-MM-DD)")
    qualifications = subparsers.add_parser(
        "ingest-qualifications", help="Validate and preserve the Ofqual qualifications and organisations CSVs"
    )
    qualifications.add_argument("qualifications_file", type=Path)
    qualifications.add_argument("organisations_file", type=Path)
    qualifications.add_argument("--published-at", type=date.fromisoformat, help="Snapshot date (YYYY-MM-DD)")
    food = subparsers.add_parser("ingest-food", help="Validate and preserve the FSA food hygiene CSV")
    food.add_argument("file", type=Path)
    food.add_argument("--published-at", type=date.fromisoformat, help="Snapshot date (YYYY-MM-DD)")
    postcodes = subparsers.add_parser("ingest-postcodes", help="Validate and preserve an OS Code-Point Open ZIP")
    postcodes.add_argument("file", type=Path)
    postcodes.add_argument("--published-at", type=date.fromisoformat, help="Snapshot date (YYYY-MM-DD)")
    properties = subparsers.add_parser("ingest-property-sales", help="Validate and preserve HM Land Registry Price Paid CSVs")
    properties.add_argument("files", type=Path, nargs="+")
    properties.add_argument("--published-at", type=date.fromisoformat, help="Snapshot date (YYYY-MM-DD)")
    study = subparsers.add_parser("ingest-study-providers", help="Import UKVI student sponsors and the OfS Register")
    study.add_argument("student_sponsors_file", type=Path)
    study.add_argument("ofs_register_file", type=Path)
    study.add_argument("--published-at", type=date.fromisoformat, help="Snapshot date (YYYY-MM-DD)")
    units = subparsers.add_parser("ingest-qualification-units", help="Import Ofqual units and mappings")
    units.add_argument("units_file", type=Path)
    units.add_argument("mappings_file", type=Path)
    units.add_argument("--published-at", type=date.fromisoformat, help="Snapshot date (YYYY-MM-DD)")
    wales = subparsers.add_parser("ingest-welsh-qualifications", help="Import the QiW complete English CSV")
    wales.add_argument("file", type=Path)
    wales.add_argument("--published-at", type=date.fromisoformat, help="Snapshot date (YYYY-MM-DD)")
    schools = subparsers.add_parser("ingest-schools", help="Import the GIAS establishment register CSV")
    schools.add_argument("file", type=Path)
    schools.add_argument("--published-at", type=date.fromisoformat, help="Snapshot date (YYYY-MM-DD)")
    ofsted = subparsers.add_parser("ingest-ofsted-inspections", help="Import the Ofsted state-funded schools inspections CSV")
    ofsted.add_argument("file", type=Path)
    ofsted.add_argument("--published-at", type=date.fromisoformat, help="Snapshot date (YYYY-MM-DD)")
    refresh = subparsers.add_parser("refresh-due", help="Fetch and ingest every source whose refresh cadence has elapsed")
    refresh.add_argument("--source", help="Only refresh this source ID")
    refresh.add_argument("--force", action="store_true", help="Refresh even if not yet due")
    args = parser.parse_args()
    if args.command == "ingest-sponsors":
        try:
            manifest = ingest_sponsor_file(args.file, args.published_at)
        except (FileNotFoundError, SponsorSchemaError) as error:
            parser.error(str(error))
    elif args.command == "ingest-qualifications":
        try:
            manifest = ingest_qualification_files(
                args.qualifications_file,
                args.organisations_file,
                args.published_at,
            )
        except (FileNotFoundError, QualificationSchemaError) as error:
            parser.error(str(error))
    elif args.command == "ingest-food":
        try:
            manifest = ingest_food_file(args.file, args.published_at)
        except (FileNotFoundError, FoodSchemaError) as error:
            parser.error(str(error))
    elif args.command == "ingest-postcodes":
        try:
            manifest = ingest_postcode_file(args.file, args.published_at)
        except (FileNotFoundError, PostcodeSchemaError) as error:
            parser.error(str(error))
    elif args.command == "ingest-property-sales":
        try:
            manifest = ingest_property_files(args.files, args.published_at)
        except (FileNotFoundError, PropertySchemaError) as error:
            parser.error(str(error))
    elif args.command == "ingest-study-providers":
        try:
            manifest = ingest_study_provider_files(args.student_sponsors_file, args.ofs_register_file, args.published_at)
        except (FileNotFoundError, StudySchemaError) as error:
            parser.error(str(error))
    elif args.command == "ingest-qualification-units":
        try:
            manifest = ingest_qualification_unit_files(args.units_file, args.mappings_file, args.published_at)
        except (FileNotFoundError, QualificationUnitSchemaError) as error:
            parser.error(str(error))
    elif args.command == "ingest-welsh-qualifications":
        try:
            manifest = ingest_welsh_qualification_file(args.file, args.published_at)
        except (FileNotFoundError, QualificationExpansionSchemaError) as error:
            parser.error(str(error))
    elif args.command == "ingest-schools":
        try:
            manifest = ingest_school_file(args.file, args.published_at)
        except (FileNotFoundError, GiasSchemaError) as error:
            parser.error(str(error))
    elif args.command == "ingest-ofsted-inspections":
        try:
            manifest = ingest_ofsted_file(args.file, args.published_at)
        except (FileNotFoundError, OfstedSchemaError) as error:
            parser.error(str(error))
    else:
        from app.services.refresh import refresh_due_sources

        manifest = refresh_due_sources(only=args.source, force=args.force)
    print(json.dumps(manifest, indent=2, default=str))


if __name__ == "__main__":
    main()
