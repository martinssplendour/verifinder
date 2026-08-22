import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect


BACKEND_DIR = Path(__file__).resolve().parents[1]


def test_billing_migrations_create_only_transactional_tables(tmp_path):
    database = tmp_path / "billing.sqlite3"
    environment = os.environ.copy()
    environment["TRANSACTION_DATABASE_URL"] = f"sqlite:///{database.as_posix()}"
    environment["TRANSACTION_MIGRATION_DATABASE_URL"] = f"sqlite:///{database.as_posix()}"

    subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "billing_alembic.ini", "upgrade", "head"],
        cwd=BACKEND_DIR,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )

    tables = set(inspect(create_engine(f"sqlite:///{database.as_posix()}")).get_table_names())
    assert tables == {"billing_alembic_version", "profiles", "usage_events"}
