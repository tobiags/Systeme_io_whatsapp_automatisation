"""Add testimonials_url to challenge_editions.

Revision ID: 009
Revises: 008
Create Date: 2026-06-08
"""
from alembic import op
import sqlalchemy as sa

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "challenge_editions",
        sa.Column("testimonials_url", sa.String(512), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("challenge_editions", "testimonials_url")
