"""Add saved decision plans.

Revision ID: 20260822_0008
Revises: 20260822_0007
"""

from alembic import op

from app.database import Base
from app import models  # noqa: F401

revision = "20260822_0008"
down_revision = "20260822_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    op.drop_table("decision_plan_records")
