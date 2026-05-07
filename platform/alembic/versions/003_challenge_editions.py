"""add challenge_editions + edition_key on campaign_enrollments

Revision ID: 003
Revises: 002
Create Date: 2026-05-07
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "challenge_editions",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("campaign_key", sa.String(128), nullable=False),
        sa.Column("edition_key", sa.String(64), nullable=False, unique=True),
        sa.Column("cohort", sa.String(16), nullable=False),
        sa.Column("edition_date", sa.String(32), nullable=False),
        sa.Column("streamyard_url", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_challenge_editions_edition_key", "challenge_editions", ["edition_key"])

    # Add edition_key to existing campaign_enrollments (nullable — existing rows get NULL)
    op.add_column(
        "campaign_enrollments",
        sa.Column("edition_key", sa.String(64), nullable=True),
    )
    op.create_index("ix_campaign_enrollments_edition_key", "campaign_enrollments", ["edition_key"])


def downgrade() -> None:
    op.drop_index("ix_campaign_enrollments_edition_key", table_name="campaign_enrollments")
    op.drop_column("campaign_enrollments", "edition_key")
    op.drop_index("ix_challenge_editions_edition_key", table_name="challenge_editions")
    op.drop_table("challenge_editions")
