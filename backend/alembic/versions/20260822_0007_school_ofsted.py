"""Add school (GIAS) and Ofsted inspection records.

Revision ID: 20260822_0007
Revises: 20260822_0006
"""

from alembic import op

from app.database import Base
from app import models  # noqa: F401

revision = "20260822_0007"
down_revision = "20260822_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    op.drop_table("ofsted_inspection_records")
    op.drop_table("school_records")
