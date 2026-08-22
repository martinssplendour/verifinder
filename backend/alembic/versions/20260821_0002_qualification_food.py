"""Add qualification and food-check source records.

Revision ID: 20260821_0002
Revises: 20260821_0001
"""

from alembic import op

from app.database import Base
from app import models  # noqa: F401

revision = "20260821_0002"
down_revision = "20260821_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    op.drop_table("food_establishment_records")
    op.drop_table("qualification_records")
    op.drop_table("awarding_organisation_records")
