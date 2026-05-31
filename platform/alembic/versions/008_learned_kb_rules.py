"""add wati_training_batches and learned_kb_rules tables

Revision ID: 008
Revises: 007
Create Date: 2026-06-01
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "wati_training_batches",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("filename", sa.String(256), nullable=True),
        sa.Column("row_count", sa.Integer(), nullable=False, default=0),
        sa.Column("conversation_count", sa.Integer(), nullable=False, default=0),
        sa.Column("rules_extracted", sa.Integer(), nullable=False, default=0),
    )

    op.create_table(
        "learned_kb_rules",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("batch_id", sa.Integer(), sa.ForeignKey("wati_training_batches.id"), nullable=True),
        sa.Column("intent", sa.String(128), nullable=False),
        sa.Column("keywords", sa.JSON(), nullable=False),
        sa.Column("suggested_reply", sa.String(1024), nullable=False),
        sa.Column("frequency", sa.Integer(), nullable=False, default=1),
        sa.Column("active", sa.Boolean(), nullable=False, default=False),
        sa.Column("needs_human", sa.Boolean(), nullable=False, default=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_learned_kb_rules_active", "learned_kb_rules", ["active"])


def downgrade() -> None:
    op.drop_index("ix_learned_kb_rules_active", table_name="learned_kb_rules")
    op.drop_table("learned_kb_rules")
    op.drop_table("wati_training_batches")
