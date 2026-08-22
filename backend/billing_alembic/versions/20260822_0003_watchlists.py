"""Add watchlists, watchlist alerts and company snapshots.

Revision ID: 20260822_billing_0003
Revises: 20260822_billing_0002
"""

import sqlalchemy as sa
from alembic import op


revision = "20260822_billing_0003"
down_revision = "20260822_billing_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "watchlist_entries",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("subject_id", sa.String(length=64), nullable=False),
        sa.Column("entity_type", sa.String(length=40), nullable=False),
        sa.Column("entity_id", sa.String(length=120), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False, unique=True),
        sa.Column("label", sa.String(length=300), nullable=True),
        sa.Column("notifications_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_watchlist_entries_subject_id", "watchlist_entries", ["subject_id"])
    op.create_index(
        "ix_watchlist_subject_entity",
        "watchlist_entries",
        ["subject_id", "entity_type", "entity_id"],
        unique=True,
    )

    op.create_table(
        "watchlist_alerts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("watchlist_entry_id", sa.Integer(), nullable=False),
        sa.Column("subject_id", sa.String(length=64), nullable=False),
        sa.Column("entity_type", sa.String(length=40), nullable=False),
        sa.Column("entity_id", sa.String(length=120), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("detail", sa.JSON(), nullable=True),
        sa.Column("email_status", sa.String(length=20), nullable=False),
        sa.Column("email_error", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["watchlist_entry_id"], ["watchlist_entries.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_watchlist_alerts_watchlist_entry_id", "watchlist_alerts", ["watchlist_entry_id"])
    op.create_index("ix_watchlist_alerts_subject_id", "watchlist_alerts", ["subject_id"])

    op.create_table(
        "company_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("company_number", sa.String(length=12), nullable=False),
        sa.Column("company_status", sa.String(length=80), nullable=True),
        sa.Column("sic_codes_hash", sa.String(length=64), nullable=True),
        sa.Column("accounts_next_due", sa.String(length=40), nullable=True),
        sa.Column("officer_count", sa.Integer(), nullable=True),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_company_snapshot_number_checked", "company_snapshots", ["company_number", "checked_at"])


def downgrade() -> None:
    op.drop_index("ix_company_snapshot_number_checked", table_name="company_snapshots")
    op.drop_table("company_snapshots")
    op.drop_index("ix_watchlist_alerts_subject_id", table_name="watchlist_alerts")
    op.drop_index("ix_watchlist_alerts_watchlist_entry_id", table_name="watchlist_alerts")
    op.drop_table("watchlist_alerts")
    op.drop_index("ix_watchlist_subject_entity", table_name="watchlist_entries")
    op.drop_index("ix_watchlist_entries_subject_id", table_name="watchlist_entries")
    op.drop_table("watchlist_entries")
