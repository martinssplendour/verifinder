"""Add composite indexes for qualification and food search.

Revision ID: 20260821_0003
Revises: 20260821_0002
Create Date: 2026-08-21
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260821_0003"
down_revision: str | None = "20260821_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_qualification_version_normalised_number",
        "qualification_records",
        ["dataset_version_id", "normalised_number"],
    )
    op.create_index(
        "ix_qualification_version_normalised_title",
        "qualification_records",
        ["dataset_version_id", "normalised_title"],
    )
    op.create_index(
        "ix_food_version_normalised_name",
        "food_establishment_records",
        ["dataset_version_id", "normalised_name"],
    )
    op.create_index(
        "ix_food_version_normalised_postcode",
        "food_establishment_records",
        ["dataset_version_id", "normalised_postcode"],
    )


def downgrade() -> None:
    op.drop_index("ix_food_version_normalised_postcode", table_name="food_establishment_records")
    op.drop_index("ix_food_version_normalised_name", table_name="food_establishment_records")
    op.drop_index("ix_qualification_version_normalised_title", table_name="qualification_records")
    op.drop_index("ix_qualification_version_normalised_number", table_name="qualification_records")
