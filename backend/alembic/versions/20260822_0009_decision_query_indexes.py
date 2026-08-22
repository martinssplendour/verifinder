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
    op.create_index("ix_property_version_town", "property_sale_records", ["dataset_version_id", "town_city"])
    op.create_index("ix_property_version_district", "property_sale_records", ["dataset_version_id", "district"])


def downgrade() -> None:
    op.drop_index("ix_property_version_district", table_name="property_sale_records")
    op.drop_index("ix_property_version_town", table_name="property_sale_records")
