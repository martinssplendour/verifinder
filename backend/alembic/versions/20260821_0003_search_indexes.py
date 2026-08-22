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
    # IF NOT EXISTS: models.py already defines these indexes, so replaying every
    # migration on a fresh database has 0001_initial's create_all() create them first.
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_qualification_version_normalised_number "
        "ON qualification_records (dataset_version_id, normalised_number)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_qualification_version_normalised_title "
        "ON qualification_records (dataset_version_id, normalised_title)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_food_version_normalised_name "
        "ON food_establishment_records (dataset_version_id, normalised_name)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_food_version_normalised_postcode "
        "ON food_establishment_records (dataset_version_id, normalised_postcode)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_food_version_normalised_postcode")
    op.execute("DROP INDEX IF EXISTS ix_food_version_normalised_name")
    op.execute("DROP INDEX IF EXISTS ix_qualification_version_normalised_title")
    op.execute("DROP INDEX IF EXISTS ix_qualification_version_normalised_number")
