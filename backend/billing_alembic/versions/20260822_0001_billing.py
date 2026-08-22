"""Create transactional entitlement tables.

Revision ID: 20260822_billing_0001
Revises: None
"""

import sqlalchemy as sa
from alembic import op


revision = "20260822_billing_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "profiles",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("email", sa.String(length=320), nullable=True, unique=True),
        sa.Column("tier", sa.Enum("FREE", "PLUS", "PROFESSIONAL", name="subscriptiontier", native_enum=False), nullable=False),
        sa.Column("stripe_customer_id", sa.String(length=80), nullable=True, unique=True),
        sa.Column("stripe_subscription_id", sa.String(length=80), nullable=True),
        sa.Column("subscription_status", sa.String(length=40), nullable=True),
        sa.Column("subscription_current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "usage_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("subject_id", sa.String(length=64), nullable=False),
        sa.Column("feature", sa.String(length=40), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_usage_events_subject_id", "usage_events", ["subject_id"])
    op.create_index(
        "ix_usage_events_subject_feature_created",
        "usage_events",
        ["subject_id", "feature", "created_at"],
    )


def downgrade() -> None:
    op.drop_table("usage_events")
    op.drop_table("profiles")
