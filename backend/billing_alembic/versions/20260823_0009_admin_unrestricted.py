"""Repair the primary VeriFinder administrator grant.

Revision ID: 20260823_billing_0009
Revises: 20260823_billing_0008
"""

from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op


revision = "20260823_billing_0009"
down_revision = "20260823_billing_0008"
branch_labels = None
depends_on = None


ADMIN_EMAIL = "okhimhemartins@gmail.com"


def upgrade() -> None:
    app_admins = sa.table(
        "app_admins",
        sa.column("email", sa.String(length=320)),
        sa.column("role", sa.String(length=32)),
        sa.column("active", sa.Boolean()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    now = datetime.now(timezone.utc)
    result = op.get_bind().execute(
        app_admins.update()
        .where(app_admins.c.email == ADMIN_EMAIL)
        .values(role="admin", active=True, updated_at=now)
    )
    if result.rowcount == 0:
        op.bulk_insert(
            app_admins,
            [
                {
                    "email": ADMIN_EMAIL,
                    "role": "admin",
                    "active": True,
                    "created_at": now,
                    "updated_at": now,
                }
            ],
        )


def downgrade() -> None:
    # This data-repair migration must not revoke the grant created by 0008.
    pass
