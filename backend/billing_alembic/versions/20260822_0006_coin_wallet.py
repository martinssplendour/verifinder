"""Add prepaid Ask coin wallets and an immutable transaction ledger.

Revision ID: 20260822_billing_0006
Revises: 20260822_billing_0005
"""

import sqlalchemy as sa
from alembic import op


revision = "20260822_billing_0006"
down_revision = "20260822_billing_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "coin_wallets",
        sa.Column("subject_id", sa.String(length=64), nullable=False),
        sa.Column("balance", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("subject_id"),
        sa.CheckConstraint("balance >= 0", name="ck_coin_wallets_non_negative"),
    )
    op.create_table(
        "coin_transactions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("subject_id", sa.String(length=64), nullable=False),
        sa.Column("delta", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=40), nullable=False),
        sa.Column("reference_id", sa.String(length=120), nullable=False),
        sa.Column("balance_after", sa.Integer(), nullable=False),
        sa.Column("detail", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("reference_id"),
    )
    op.create_index("ix_coin_transactions_subject_id", "coin_transactions", ["subject_id"])
    op.create_index(
        "ix_coin_transactions_subject_created",
        "coin_transactions",
        ["subject_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_coin_transactions_subject_created", table_name="coin_transactions")
    op.drop_index("ix_coin_transactions_subject_id", table_name="coin_transactions")
    op.drop_table("coin_transactions")
    op.drop_table("coin_wallets")
