"""add per-day StreamYard URLs to challenge_editions

Revision ID: 004
Revises: 003
Create Date: 2026-05-14
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("challenge_editions", sa.Column("day1_url", sa.String(512), nullable=True))
    op.add_column("challenge_editions", sa.Column("day2_url", sa.String(512), nullable=True))
    op.add_column("challenge_editions", sa.Column("day3_url", sa.String(512), nullable=True))


def downgrade() -> None:
    op.drop_column("challenge_editions", "day3_url")
    op.drop_column("challenge_editions", "day2_url")
    op.drop_column("challenge_editions", "day1_url")
