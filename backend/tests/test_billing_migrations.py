import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect, text


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
        "app_admins",
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
    with create_engine(f"sqlite:///{database.as_posix()}").connect() as connection:
        grant = connection.execute(
            text("SELECT email, role, active FROM app_admins WHERE email = :email"),
            {"email": "okhimhemartins@gmail.com"},
        ).one()
    assert grant.email == "okhimhemartins@gmail.com"
    assert grant.role == "admin"
    assert bool(grant.active) is True


def test_latest_migration_repairs_primary_admin_grant(tmp_path):
    database = tmp_path / "billing-admin-repair.sqlite3"
    database_url = f"sqlite:///{database.as_posix()}"
    environment = os.environ.copy()
    environment["TRANSACTION_DATABASE_URL"] = database_url
    environment["TRANSACTION_MIGRATION_DATABASE_URL"] = database_url

    subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "billing_alembic.ini", "upgrade", "20260823_billing_0008"],
        cwd=BACKEND_DIR,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            text("UPDATE app_admins SET role = 'viewer', active = false WHERE email = :email"),
            {"email": "okhimhemartins@gmail.com"},
        )

    subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "billing_alembic.ini", "upgrade", "head"],
        cwd=BACKEND_DIR,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    with engine.connect() as connection:
        grant = connection.execute(
            text("SELECT role, active FROM app_admins WHERE email = :email"),
            {"email": "okhimhemartins@gmail.com"},
        ).one()

    assert grant.role == "admin"
    assert bool(grant.active) is True


def _run_alembic(target: str, environment: dict[str, str]) -> None:
    subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "billing_alembic.ini", "upgrade", target],
        cwd=BACKEND_DIR,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )


def test_admin_coin_grant_tops_up_the_wallet_of_the_matching_profile(tmp_path):
    database = tmp_path / "billing-admin-coins.sqlite3"
    database_url = f"sqlite:///{database.as_posix()}"
    environment = os.environ.copy()
    environment["TRANSACTION_DATABASE_URL"] = database_url
    environment["TRANSACTION_MIGRATION_DATABASE_URL"] = database_url

    _run_alembic("20260823_billing_0009", environment)
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO profiles (id, email, tier, created_at, updated_at)"
                " VALUES ('subject-admin', 'okhimhemartins@gmail.com', 'FREE',"
                " '2026-08-24 00:00:00+00:00', '2026-08-24 00:00:00+00:00')"
            )
        )

    _run_alembic("head", environment)
    with engine.connect() as connection:
        wallet = connection.execute(
            text("SELECT balance FROM coin_wallets WHERE subject_id = 'subject-admin'")
        ).one()
        ledger = connection.execute(
            text(
                "SELECT delta, reason, balance_after FROM coin_transactions"
                " WHERE reference_id = 'admin-unlimited:okhimhemartins@gmail.com'"
            )
        ).one()

    assert wallet.balance == 1_000_000_000
    assert ledger.reason == "grant"
    assert ledger.balance_after == 1_000_000_000


def test_admin_coin_grant_is_not_applied_twice(tmp_path):
    database = tmp_path / "billing-admin-coins-repeat.sqlite3"
    database_url = f"sqlite:///{database.as_posix()}"
    environment = os.environ.copy()
    environment["TRANSACTION_DATABASE_URL"] = database_url
    environment["TRANSACTION_MIGRATION_DATABASE_URL"] = database_url

    _run_alembic("20260823_billing_0009", environment)
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO profiles (id, email, tier, created_at, updated_at)"
                " VALUES ('subject-admin', 'okhimhemartins@gmail.com', 'FREE',"
                " '2026-08-24 00:00:00+00:00', '2026-08-24 00:00:00+00:00')"
            )
        )
    _run_alembic("head", environment)

    # Spending against the grant must not be undone by a later migration run.
    with engine.begin() as connection:
        connection.execute(
            text("UPDATE coin_wallets SET balance = 12 WHERE subject_id = 'subject-admin'")
        )
    _run_alembic("head", environment)

    with engine.connect() as connection:
        balance = connection.execute(
            text("SELECT balance FROM coin_wallets WHERE subject_id = 'subject-admin'")
        ).scalar()
        grants = connection.execute(
            text(
                "SELECT count(*) FROM coin_transactions"
                " WHERE reference_id = 'admin-unlimited:okhimhemartins@gmail.com'"
            )
        ).scalar()

    assert balance == 12
    assert grants == 1


def test_admin_coin_grant_is_skipped_when_no_profile_matches(tmp_path):
    database = tmp_path / "billing-admin-coins-absent.sqlite3"
    database_url = f"sqlite:///{database.as_posix()}"
    environment = os.environ.copy()
    environment["TRANSACTION_DATABASE_URL"] = database_url
    environment["TRANSACTION_MIGRATION_DATABASE_URL"] = database_url

    _run_alembic("head", environment)
    with create_engine(database_url).connect() as connection:
        wallets = connection.execute(text("SELECT count(*) FROM coin_wallets")).scalar()

    assert wallets == 0
