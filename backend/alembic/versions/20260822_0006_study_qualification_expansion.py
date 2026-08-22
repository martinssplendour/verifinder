"""Add study-provider and qualification-expansion records.

Revision ID: 20260822_0006
Revises: 20260822_0005
"""

from alembic import op

from app.database import Base
from app import models  # noqa: F401

revision = "20260822_0006"
down_revision = "20260822_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    op.drop_table("qualification_unit_mappings")
    op.drop_table("qualification_unit_records")
    op.drop_table("qualification_expansion_records")
    op.drop_table("ofs_provider_records")
    op.drop_table("student_sponsor_records")
