"""add contact_scores, score_events, inbound_messages

Revision ID: 002
Revises: 001
Create Date: 2026-05-07
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "contact_scores",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("contact_id", sa.String(32), nullable=False),
        sa.Column("total_score", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_updated", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("contact_id", name="uq_contact_scores_contact_id"),
    )
    op.create_index("ix_contact_scores_contact_id", "contact_scores", ["contact_id"])

    op.create_table(
        "score_events",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("contact_id", sa.String(32), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("points", sa.Integer, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_score_events_contact_id", "score_events", ["contact_id"])

    op.create_table(
        "inbound_messages",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("phone", sa.String(32), nullable=False),
        sa.Column("contact_id", sa.String(32), nullable=True),
        sa.Column("text", sa.String(4096), nullable=False),
        sa.Column("ai_reply", sa.String(4096), nullable=True),
        sa.Column("needs_human", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("intent", sa.String(64), nullable=False, server_default="'default'"),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_inbound_messages_phone", "inbound_messages", ["phone"])


def downgrade() -> None:
    op.drop_index("ix_inbound_messages_phone", table_name="inbound_messages")
    op.drop_table("inbound_messages")
    op.drop_index("ix_score_events_contact_id", table_name="score_events")
    op.drop_table("score_events")
    op.drop_index("ix_contact_scores_contact_id", table_name="contact_scores")
    op.drop_table("contact_scores")
