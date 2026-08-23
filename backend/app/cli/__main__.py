import argparse
import json
from datetime import date
from pathlib import Path

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
from app.services.food_ingestion import FoodSchemaError
from app.services.gias_ingestion import GiasSchemaError
from app.services.ofsted_ingestion import OfstedSchemaError
from app.services.postcode_ingestion import PostcodeSchemaError
from app.services.property_ingestion import PropertySchemaError
from app.services.qualification_ingestion import QualificationSchemaError
from app.services.qualification_expansion_ingestion import QualificationExpansionSchemaError
from app.services.qualification_unit_ingestion import QualificationUnitSchemaError
from app.services.sponsor_ingestion import SponsorSchemaError
from app.services.study_ingestion import StudySchemaError


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
