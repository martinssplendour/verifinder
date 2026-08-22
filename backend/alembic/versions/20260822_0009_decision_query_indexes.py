"""Add decision-query property indexes.

Revision ID: 20260822_0009
Revises: 20260822_0008
"""

from alembic import op

revision = "20260822_0009"
down_revision = "20260822_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_property_version_town "
        "ON property_sale_records (dataset_version_id, town_city)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_property_version_district "
        "ON property_sale_records (dataset_version_id, district)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_property_version_district")
    op.execute("DROP INDEX IF EXISTS ix_property_version_town")
