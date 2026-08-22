"""Remove obsolete server-side decision plan storage.

Revision ID: 20260822_0010
Revises: 20260822_0009
"""

import sqlalchemy as sa
from alembic import op

revision = "20260822_0010"
down_revision = "20260822_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "decision_plan_records" in inspector.get_table_names():
        op.drop_table("decision_plan_records")


def downgrade() -> None:
    op.create_table(
        "decision_plan_records",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("user_goal", sa.Text(), nullable=False),
        sa.Column("location", sa.String(length=180), nullable=True),
        sa.Column("template", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("request_payload", sa.JSON(), nullable=False),
        sa.Column("response_payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
