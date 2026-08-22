import gzip
import hashlib
import sqlite3

import pytest

from app.database_snapshot import (
    _database_path,
    _expand_snapshot,
    _is_valid_database,
    _validate_snapshot_url,
)


def test_snapshot_expands_to_a_valid_sqlite_database(tmp_path):
    source = tmp_path / "source.sqlite3"
    with sqlite3.connect(source) as connection:
        connection.execute("CREATE TABLE evidence (value TEXT NOT NULL)")
        connection.execute("INSERT INTO evidence VALUES ('verified')")

    archive = tmp_path / "source.sqlite3.gz"
    with source.open("rb") as input_file, gzip.open(archive, "wb") as output_file:
        output_file.write(input_file.read())
    assert len(hashlib.sha256(archive.read_bytes()).hexdigest()) == 64

    expanded = tmp_path / "expanded.sqlite3"
    _expand_snapshot(archive, expanded)
    assert _is_valid_database(expanded)


def test_database_path_requires_file_backed_sqlite():
    with pytest.raises(ValueError):
        _database_path("postgresql+psycopg://example.test/verifinder")


def test_snapshot_url_requires_https():
    with pytest.raises(ValueError):
        _validate_snapshot_url("http://example.test/database.sqlite3.gz")
