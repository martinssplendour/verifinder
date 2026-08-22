"""Persist bounded Ask conversation context.

Revision ID: 20260822_billing_0007
Revises: 20260822_billing_0006
"""

import sqlalchemy as sa
from alembic import op


revision = "20260822_billing_0007"
down_revision = "20260822_billing_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ask_conversations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("subject_id", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ask_conversations_subject_id", "ask_conversations", ["subject_id"])
    op.create_index(
        "ix_ask_conversations_subject_updated",
        "ask_conversations",
        ["subject_id", "updated_at"],
    )
    op.create_table(
        "ask_conversation_records",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("conversation_id", sa.String(length=36), nullable=False),
        sa.Column("response", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["ask_conversations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ask_conversation_records_conversation_id",
        "ask_conversation_records",
        ["conversation_id"],
    )
    op.create_index(
        "ix_ask_records_conversation_created",
        "ask_conversation_records",
        ["conversation_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_ask_records_conversation_created", table_name="ask_conversation_records")
    op.drop_index("ix_ask_conversation_records_conversation_id", table_name="ask_conversation_records")
    op.drop_table("ask_conversation_records")
    op.drop_index("ix_ask_conversations_subject_updated", table_name="ask_conversations")
    op.drop_index("ix_ask_conversations_subject_id", table_name="ask_conversations")
    op.drop_table("ask_conversations")
