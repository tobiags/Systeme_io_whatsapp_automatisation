"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-05-06
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "contacts",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("phone", sa.String(32), nullable=False, unique=True),
        sa.Column("first_name", sa.String(100), nullable=True),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_contacts_phone", "contacts", ["phone"])

    op.create_table(
        "consents",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("contact_id", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("proof_source", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_consents_contact_id", "consents", ["contact_id"])

    op.create_table(
        "messages",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("contact_id", sa.String(32), nullable=False),
        sa.Column("template_key", sa.String(128), nullable=False),
        sa.Column("variables", sa.JSON, nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_messages_contact_id", "messages", ["contact_id"])

    op.create_table(
        "campaign_enrollments",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("contact_id", sa.String(32), nullable=False),
        sa.Column("campaign_key", sa.String(128), nullable=False),
        sa.Column("current_step", sa.String(64), nullable=False),
        sa.Column("cohort", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_campaign_enrollments_contact_id", "campaign_enrollments", ["contact_id"])

    op.create_table(
        "scores",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("contact_id", sa.String(32), nullable=False),
        sa.Column("events", sa.JSON, nullable=False),
        sa.Column("score", sa.Integer, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_scores_contact_id", "scores", ["contact_id"])

    op.create_table(
        "segments",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("contact_id", sa.String(32), nullable=False),
        sa.Column("segment", sa.String(32), nullable=False),
        sa.Column("score", sa.Integer, nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_segments_contact_id", "segments", ["contact_id"])

    op.create_table(
        "audit_events",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("aggregate_id", sa.String(128), nullable=False),
        sa.Column("payload", sa.JSON, nullable=False),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_events_name", "audit_events", ["name"])
    op.create_index("ix_audit_events_aggregate_id", "audit_events", ["aggregate_id"])

    op.create_table(
        "lab_evaluations",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("candidate_id", sa.String(128), nullable=False),
        sa.Column("candidate_type", sa.String(64), nullable=False),
        sa.Column("score", sa.Float, nullable=False),
        sa.Column("recommended", sa.Boolean, nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("lab_evaluations")
    op.drop_table("audit_events")
    op.drop_table("segments")
    op.drop_table("scores")
    op.drop_table("campaign_enrollments")
    op.drop_table("messages")
    op.drop_table("consents")
    op.drop_table("contacts")
