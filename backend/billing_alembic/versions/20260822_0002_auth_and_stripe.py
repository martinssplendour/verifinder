"""Add authenticated profiles, subscriptions and Stripe event ledger.

Revision ID: 20260822_billing_0002
Revises: 20260822_billing_0001
"""

import sqlalchemy as sa
from alembic import op


revision = "20260822_billing_0002"
down_revision = "20260822_billing_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("profiles") as batch:
        batch.add_column(sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))

    op.execute("UPDATE profiles SET updated_at = created_at WHERE updated_at IS NULL")

    op.create_table(
        "subscriptions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("tier", sa.Enum("FREE", "PLUS", "PROFESSIONAL", name="subscriptiontier", native_enum=False), nullable=False),
        sa.Column("provider", sa.String(length=24), nullable=False),
        sa.Column("customer_id", sa.String(length=80), nullable=True, unique=True),
        sa.Column("subscription_id", sa.String(length=80), nullable=True, unique=True),
        sa.Column("status", sa.String(length=40), nullable=True),
        sa.Column("price_id", sa.String(length=80), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["profiles.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_subscriptions_user_id", "subscriptions", ["user_id"], unique=True)

    op.create_table(
        "stripe_events",
        sa.Column("event_id", sa.String(length=80), primary_key=True),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False),
    )

    with op.batch_alter_table("usage_events") as batch:
        batch.add_column(sa.Column("network_hash", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("quota_key", sa.String(length=96), nullable=True))
        batch.create_index("ix_usage_events_network_hash", ["network_hash"], unique=False)
        batch.create_unique_constraint("uq_usage_events_quota_key", ["quota_key"])


def downgrade() -> None:
    with op.batch_alter_table("usage_events") as batch:
        batch.drop_constraint("uq_usage_events_quota_key", type_="unique")
        batch.drop_index("ix_usage_events_network_hash")
        batch.drop_column("quota_key")
        batch.drop_column("network_hash")
    op.drop_table("stripe_events")
    op.drop_index("ix_subscriptions_user_id", table_name="subscriptions")
    op.drop_table("subscriptions")
    with op.batch_alter_table("profiles") as batch:
        batch.drop_column("updated_at")
