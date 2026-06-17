"""Add closer_wati_email to challenge_editions.

Revision ID: 011
Revises: 010
Create Date: 2026-06-17
"""
from alembic import op
import sqlalchemy as sa

revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "challenge_editions",
        sa.Column("closer_wati_email", sa.String(256), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("challenge_editions", "closer_wati_email")
