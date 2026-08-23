"""Add database-backed VeriFinder administrator grants.

Revision ID: 20260823_billing_0008
Revises: 20260822_billing_0007
"""

from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op


revision = "20260823_billing_0008"
down_revision = "20260822_billing_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "app_admins",
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False, server_default="admin"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("email"),
    )
    now = datetime.now(timezone.utc)
    app_admins = sa.table(
        "app_admins",
        sa.column("email", sa.String(length=320)),
        sa.column("role", sa.String(length=32)),
        sa.column("active", sa.Boolean()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    op.bulk_insert(
        app_admins,
        [
            {
                "email": "okhimhemartins@gmail.com",
                "role": "admin",
                "active": True,
                "created_at": now,
                "updated_at": now,
            }
        ],
    )


def downgrade() -> None:
    op.drop_table("app_admins")
