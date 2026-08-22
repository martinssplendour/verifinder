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

    inspector = inspect(create_engine(f"sqlite:///{database.as_posix()}"))
    tables = set(inspector.get_table_names())
    assert tables == {
        "billing_alembic_version",
        "coin_transactions",
        "coin_wallets",
        "ask_conversation_records",
        "ask_conversations",
        "profiles",
        "stripe_events",
        "subscriptions",
        "usage_events",
        "watchlist_entries",
        "watchlist_alerts",
        "company_snapshots",
        "saved_reports",
        "watch_snapshots",
        "operation_checks",
        "scheduler_leases",
    }
    alert_columns = {column["name"] for column in inspector.get_columns("watchlist_alerts")}
    assert "fingerprint" in alert_columns
    # Coin ledgers intentionally avoid REFERENCES on profiles because the
    # Supabase migration role may not own that pre-existing table.
    assert inspector.get_foreign_keys("coin_wallets") == []
    assert inspector.get_foreign_keys("coin_transactions") == []
