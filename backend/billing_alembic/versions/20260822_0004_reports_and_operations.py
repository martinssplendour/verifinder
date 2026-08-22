"""Add persisted reports and operational scheduler state.

Revision ID: 20260822_billing_0004
Revises: 20260822_billing_0003
"""

import sqlalchemy as sa
from alembic import op


revision = "20260822_billing_0004"
down_revision = "20260822_billing_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "saved_reports",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("subject_id", sa.String(length=64), nullable=False),
        sa.Column("source_report_id", sa.String(length=80), nullable=False),
        sa.Column("report_type", sa.String(length=40), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("storage_bucket", sa.String(length=100), nullable=False),
        sa.Column("storage_path", sa.String(length=700), nullable=False, unique=True),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("provenance_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_saved_reports_subject_id", "saved_reports", ["subject_id"])
    op.create_index("ix_saved_reports_subject_created", "saved_reports", ["subject_id", "created_at"])
    op.create_index("ix_saved_reports_subject_source", "saved_reports", ["subject_id", "source_report_id"], unique=True)

    op.create_table(
        "watch_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("watchlist_entry_id", sa.Integer(), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("detail", sa.JSON(), nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["watchlist_entry_id"], ["watchlist_entries.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_watch_snapshots_watchlist_entry_id", "watch_snapshots", ["watchlist_entry_id"])
    op.create_index("ix_watch_snapshots_entry_checked", "watch_snapshots", ["watchlist_entry_id", "checked_at"])

    op.create_table(
        "operation_checks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("check_name", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("detail", sa.JSON(), nullable=True),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_operation_checks_check_name", "operation_checks", ["check_name"])
    op.create_index("ix_operation_checks_name_checked", "operation_checks", ["check_name", "checked_at"])

    op.create_table(
        "scheduler_leases",
        sa.Column("job_name", sa.String(length=80), primary_key=True),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_status", sa.String(length=20), nullable=True),
        sa.Column("last_detail", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("scheduler_leases")
    op.drop_index("ix_operation_checks_name_checked", table_name="operation_checks")
    op.drop_index("ix_operation_checks_check_name", table_name="operation_checks")
    op.drop_table("operation_checks")
    op.drop_index("ix_watch_snapshots_entry_checked", table_name="watch_snapshots")
    op.drop_index("ix_watch_snapshots_watchlist_entry_id", table_name="watch_snapshots")
    op.drop_table("watch_snapshots")
    op.drop_index("ix_saved_reports_subject_created", table_name="saved_reports")
    op.drop_index("ix_saved_reports_subject_source", table_name="saved_reports")
    op.drop_index("ix_saved_reports_subject_id", table_name="saved_reports")
    op.drop_table("saved_reports")
