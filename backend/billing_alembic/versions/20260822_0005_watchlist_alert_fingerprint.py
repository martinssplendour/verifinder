"""Add the watchlist alert fingerprint used for deduplication.

Revision ID: 20260822_billing_0005
Revises: 20260822_billing_0004
"""

import hashlib

import sqlalchemy as sa
from alembic import op


revision = "20260822_billing_0005"
down_revision = "20260822_billing_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("watchlist_alerts") as batch:
        batch.add_column(sa.Column("fingerprint", sa.String(length=64), nullable=True))

    connection = op.get_bind()
    rows = connection.execute(sa.text("select id from watchlist_alerts where fingerprint is null")).fetchall()
    for (alert_id,) in rows:
        fingerprint = hashlib.sha256(f"legacy-watchlist-alert:{alert_id}".encode()).hexdigest()
        connection.execute(
            sa.text("update watchlist_alerts set fingerprint = :fingerprint where id = :alert_id"),
            {"fingerprint": fingerprint, "alert_id": alert_id},
        )

    with op.batch_alter_table("watchlist_alerts") as batch:
        batch.alter_column("fingerprint", existing_type=sa.String(length=64), nullable=False)
        batch.create_index("ux_watchlist_alerts_fingerprint", ["fingerprint"], unique=True)


def downgrade() -> None:
    with op.batch_alter_table("watchlist_alerts") as batch:
        batch.drop_index("ux_watchlist_alerts_fingerprint")
        batch.drop_column("fingerprint")
