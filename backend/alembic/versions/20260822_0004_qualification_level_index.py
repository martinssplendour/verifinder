"""Add a composite index for qualification level filtering.

Revision ID: 20260822_0004
Revises: 20260821_0003
Create Date: 2026-08-22
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260822_0004"
down_revision: str | None = "20260821_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_qualification_version_level",
        "qualification_records",
        ["dataset_version_id", "level"],
    )


def downgrade() -> None:
    op.drop_index("ix_qualification_version_level", table_name="qualification_records")
