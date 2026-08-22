from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from app.config import get_settings
from app.database_snapshot import _database_path


PUBLIC_TABLES = (
    "awarding_organisation_records",
    "change_events",
    "companies",
    "data_sources",
    "dataset_versions",
    "entity_mappings",
    "food_establishment_records",
    "ingestion_runs",
    "ofs_provider_records",
    "ofsted_inspection_records",
    "postcode_records",
    "property_sale_records",
    "qualification_expansion_records",
    "qualification_records",
    "qualification_unit_mappings",
    "qualification_unit_records",
    "school_records",
    "sponsor_records",
    "student_sponsor_records",
)
MANIFEST_VERSION = 1
IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]*$")
SNAPSHOT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
STAGING_DIRECTORY = re.compile(r"^\.staging-[0-9a-f]{32}$")
DUCKDB_MEMORY_LIMIT = os.getenv("PUBLIC_DATA_EXPORT_MEMORY_LIMIT", "192MB")
DUCKDB_MAX_TEMP_SIZE = os.getenv("PUBLIC_DATA_EXPORT_MAX_TEMP_SIZE", "1GB")


def _identifier(value: str) -> str:
    if not IDENTIFIER.fullmatch(value):
        raise ValueError(f"Unsafe SQL identifier: {value!r}")
    return f'"{value}"'


def _literal(value: str | Path) -> str:
    return f"'{str(value).replace("'", "''")}'"


def _connect(temp_directory: Path | None = None) -> duckdb.DuckDBPyConnection:
    connection = duckdb.connect()
    connection.execute(f"SET memory_limit = {_literal(DUCKDB_MEMORY_LIMIT)}")
    connection.execute("SET threads = 1")
    connection.execute("SET preserve_insertion_order = false")
    if temp_directory is not None:
        temp_directory.mkdir(parents=True, exist_ok=True)
        connection.execute(f"SET temp_directory = {_literal(temp_directory.as_posix())}")
        connection.execute(f"SET max_temp_directory_size = {_literal(DUCKDB_MAX_TEMP_SIZE)}")
    try:
        connection.execute("LOAD sqlite")
    except duckdb.Error:
        connection.execute("INSTALL sqlite")
        connection.execute("LOAD sqlite")
    return connection


def _remove_staging(root: Path, staging: Path) -> None:
    if staging.parent == root and staging.name.startswith(".staging-") and not staging.is_symlink():
        shutil.rmtree(staging, ignore_errors=True)


def _remove_interrupted_exports(root: Path) -> None:
    if not root.is_dir():
        return
    for candidate in root.iterdir():
        if (
            candidate.is_dir()
            and not candidate.is_symlink()
            and STAGING_DIRECTORY.fullmatch(candidate.name)
        ):
            _remove_staging(root, candidate)
    temporary = root / ".duckdb-export-tmp"
    if temporary.is_dir() and not temporary.is_symlink():
        shutil.rmtree(temporary)


def _sqlite_tables(source: Path) -> set[str]:
    with sqlite3.connect(f"file:{source.as_posix()}?mode=ro", uri=True) as connection:
        return {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            )
        }


def export_sqlite_to_parquet(source: Path, root: Path, snapshot_id: str | None = None) -> dict:
    source = source.expanduser().resolve()
    root = root.expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"SQLite source does not exist: {source}")
    missing = sorted(set(PUBLIC_TABLES) - _sqlite_tables(source))
    if missing:
        raise RuntimeError(f"SQLite source is missing required tables: {', '.join(missing)}")

    snapshot_id = snapshot_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if not SNAPSHOT_ID.fullmatch(snapshot_id):
        raise ValueError("Snapshot ID may contain only letters, numbers, underscores, and hyphens.")
    snapshots = root / "snapshots"
    destination = snapshots / snapshot_id
    if destination.exists():
        raise FileExistsError(f"Snapshot already exists: {destination}")
    root.mkdir(parents=True, exist_ok=True)
    _remove_interrupted_exports(root)
    staging = root / f".staging-{uuid.uuid4().hex}"
    staging.mkdir(parents=True, exist_ok=False)
    temp_directory = root / ".duckdb-export-tmp"

    manifest_tables: dict[str, dict[str, int | str]] = {}
    connection = _connect(temp_directory)
    try:
        connection.execute(f"ATTACH {_literal(source.as_posix())} AS source (TYPE sqlite)")
        for table in PUBLIC_TABLES:
            parquet_file = staging / f"{table}.parquet"
            quoted = _identifier(table)
            row_count = connection.execute(f"SELECT count(*) FROM source.{quoted}").fetchone()[0]
            connection.execute(
                f"COPY (SELECT * FROM source.{quoted}) TO {_literal(parquet_file.as_posix())} "
                "(FORMAT PARQUET, COMPRESSION ZSTD, ROW_GROUP_SIZE 25000, PER_THREAD_OUTPUT false)"
            )
            manifest_tables[table] = {
                "file": parquet_file.name,
                "rows": int(row_count),
                "bytes": parquet_file.stat().st_size,
            }
    except BaseException:
        _remove_staging(root, staging)
        raise
    finally:
        connection.close()
        if temp_directory.is_dir() and not temp_directory.is_symlink():
            shutil.rmtree(temp_directory)

    manifest = {
        "manifest_version": MANIFEST_VERSION,
        "snapshot_id": snapshot_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": {"kind": "sqlite", "bytes": source.stat().st_size},
        "tables": manifest_tables,
    }
    try:
        (staging / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        snapshots.mkdir(parents=True, exist_ok=True)
        os.replace(staging, destination)
        pointer = root / ".current.json.tmp"
        pointer.write_text(
            json.dumps(
                {"snapshot_id": snapshot_id, "manifest": f"snapshots/{snapshot_id}/manifest.json"},
                indent=2,
            ),
            encoding="utf-8",
        )
        os.replace(pointer, root / "current.json")
    except BaseException:
        _remove_staging(root, staging)
        raise
    return manifest


def current_manifest(root: Path) -> tuple[Path, dict]:
    root = root.expanduser().resolve()
    pointer_path = root / "current.json"
    if not pointer_path.is_file():
        raise FileNotFoundError(f"No active Parquet snapshot pointer exists at {pointer_path}")
    pointer = json.loads(pointer_path.read_text(encoding="utf-8"))
    manifest_path = (root / pointer["manifest"]).resolve()
    if root not in manifest_path.parents:
        raise ValueError("The active manifest points outside PUBLIC_DATA_ROOT.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("manifest_version") != MANIFEST_VERSION:
        raise ValueError("Unsupported public-data manifest version.")
    return manifest_path, manifest


def verify_snapshot(root: Path) -> dict[str, int]:
    manifest_path, manifest = current_manifest(root)
    snapshot_dir = manifest_path.parent
    connection = duckdb.connect()
    verified: dict[str, int] = {}
    try:
        for table in PUBLIC_TABLES:
            item = manifest["tables"].get(table)
            if item is None:
                raise RuntimeError(f"Manifest is missing table {table}.")
            parquet_file = (snapshot_dir / item["file"]).resolve()
            if snapshot_dir not in parquet_file.parents or not parquet_file.is_file():
                raise FileNotFoundError(f"Parquet file is missing for {table}.")
            if parquet_file.stat().st_size != item["bytes"]:
                raise RuntimeError(f"Parquet file size changed for {table}.")
            count = connection.execute(
                f"SELECT count(*) FROM read_parquet({_literal(parquet_file.as_posix())})"
            ).fetchone()[0]
            if count != item["rows"]:
                raise RuntimeError(f"Parquet row count changed for {table}: expected {item['rows']}, got {count}.")
            verified[table] = int(count)
    finally:
        connection.close()
    return verified


def activate_snapshot(root: Path, catalog: Path) -> dict[str, int]:
    root = root.expanduser().resolve()
    catalog = catalog.expanduser().resolve()
    manifest_path, manifest = current_manifest(root)
    verified = verify_snapshot(root)
    snapshot_dir = manifest_path.parent
    catalog.parent.mkdir(parents=True, exist_ok=True)
    temporary = catalog.with_name(f".{catalog.name}.{uuid.uuid4().hex}.tmp")
    connection = duckdb.connect(str(temporary))
    try:
        for table in PUBLIC_TABLES:
            parquet_file = (snapshot_dir / manifest["tables"][table]["file"]).resolve()
            connection.execute(
                f"CREATE VIEW {_identifier(table)} AS "
                f"SELECT * FROM read_parquet({_literal(parquet_file.as_posix())})"
            )
        connection.execute(
            "CREATE TABLE public_data_metadata AS SELECT ? AS snapshot_id, ? AS activated_at",
            [manifest["snapshot_id"], datetime.now(timezone.utc)],
        )
        connection.execute("CHECKPOINT")
    finally:
        connection.close()
    os.replace(temporary, catalog)
    return verified


def bootstrap_data_lake() -> dict[str, int]:
    settings = get_settings()
    root = Path(settings.public_data_root)
    if not (root / "current.json").is_file():
        export_sqlite_to_parquet(_database_path(settings.database_url), root)
    return activate_snapshot(root, settings.public_catalog_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build and activate VeriFinder's local Parquet data lake")
    subparsers = parser.add_subparsers(dest="command", required=True)
    export = subparsers.add_parser("export")
    export.add_argument("--sqlite", type=Path, required=True)
    export.add_argument("--root", type=Path, required=True)
    export.add_argument("--snapshot-id")
    activate = subparsers.add_parser("activate")
    activate.add_argument("--root", type=Path, required=True)
    activate.add_argument("--catalog", type=Path, required=True)
    verify = subparsers.add_parser("verify")
    verify.add_argument("--root", type=Path, required=True)
    subparsers.add_parser("bootstrap")
    args = parser.parse_args()

    if args.command == "export":
        result = export_sqlite_to_parquet(args.sqlite, args.root, args.snapshot_id)
    elif args.command == "activate":
        result = activate_snapshot(args.root, args.catalog)
    elif args.command == "verify":
        result = verify_snapshot(args.root)
    else:
        result = bootstrap_data_lake()
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
