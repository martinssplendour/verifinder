"""Award the primary VeriFinder administrator an effectively unlimited coin balance.

Admin accounts already bypass the coin debit when asking a question, but the
wallet they are shown still reported whatever had been purchased. This tops that
wallet up so the displayed balance matches the access the account actually has.

The ledger reference makes the grant idempotent: re-running migrations, or
running them against a database that already holds the grant, credits nothing.

Revision ID: 20260824_billing_0010
Revises: 20260823_billing_0009
"""

import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op


revision = "20260824_billing_0010"
down_revision = "20260823_billing_0009"
branch_labels = None
depends_on = None


ADMIN_EMAIL = "okhimhemartins@gmail.com"
GRANT_REFERENCE = f"admin-unlimited:{ADMIN_EMAIL}"
# The wallet balance is a plain integer, so "unlimited" is expressed as a
# balance no amount of real usage can exhaust rather than a separate flag.
UNLIMITED_BALANCE = 1_000_000_000


def upgrade() -> None:
    connection = op.get_bind()
    now = datetime.now(timezone.utc)

    already_granted = connection.execute(
        sa.text("SELECT 1 FROM coin_transactions WHERE reference_id = :reference"),
        {"reference": GRANT_REFERENCE},
    ).first()
    if already_granted:
        return

    subject_id = connection.execute(
        sa.text("SELECT id FROM profiles WHERE lower(email) = :email"),
        {"email": ADMIN_EMAIL},
    ).scalar()
    if subject_id is None:
        # The account has not signed in against this database yet. Nothing to
        # credit, and inventing a wallet for an unknown subject would strand it.
        return

    balance = connection.execute(
        sa.text("SELECT balance FROM coin_wallets WHERE subject_id = :subject"),
        {"subject": subject_id},
    ).scalar()

    if balance is None:
        connection.execute(
            sa.text(
                "INSERT INTO coin_wallets (subject_id, balance, updated_at)"
                " VALUES (:subject, :balance, :now)"
            ),
            {"subject": subject_id, "balance": UNLIMITED_BALANCE, "now": now},
        )
        delta = UNLIMITED_BALANCE
    elif balance < UNLIMITED_BALANCE:
        connection.execute(
            sa.text(
                "UPDATE coin_wallets SET balance = :balance, updated_at = :now"
                " WHERE subject_id = :subject"
            ),
            {"subject": subject_id, "balance": UNLIMITED_BALANCE, "now": now},
        )
        delta = UNLIMITED_BALANCE - balance
    else:
        return

    connection.execute(
        sa.text(
            "INSERT INTO coin_transactions"
            " (id, subject_id, delta, reason, reference_id, balance_after, detail, created_at)"
            " VALUES (:id, :subject, :delta, :reason, :reference, :balance_after, :detail, :now)"
        ),
        {
            "id": str(uuid.uuid4()),
            "subject": subject_id,
            "delta": delta,
            "reason": "grant",
            "reference": GRANT_REFERENCE,
            "balance_after": UNLIMITED_BALANCE,
            "detail": '{"grant": "admin_unlimited"}',
            "now": now,
        },
    )


def downgrade() -> None:
    connection = op.get_bind()
    subject_id = connection.execute(
        sa.text("SELECT subject_id FROM coin_transactions WHERE reference_id = :reference"),
        {"reference": GRANT_REFERENCE},
    ).scalar()
    if subject_id is None:
        return
    connection.execute(
        sa.text("DELETE FROM coin_transactions WHERE reference_id = :reference"),
        {"reference": GRANT_REFERENCE},
    )
    connection.execute(
        sa.text("UPDATE coin_wallets SET balance = 0 WHERE subject_id = :subject"),
        {"subject": subject_id},
    )
