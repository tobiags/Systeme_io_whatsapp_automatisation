"""add edition-level payment, closer, and replay links

Revision ID: 006
Revises: 005
Create Date: 2026-05-22
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("challenge_editions", sa.Column("payment_url", sa.String(length=512), nullable=True))
    op.add_column("challenge_editions", sa.Column("closer_booking_url", sa.String(length=512), nullable=True))
    op.add_column("challenge_editions", sa.Column("replay_day1_url", sa.String(length=512), nullable=True))
    op.add_column("challenge_editions", sa.Column("replay_day2_url", sa.String(length=512), nullable=True))
    op.add_column("challenge_editions", sa.Column("replay_day3_url", sa.String(length=512), nullable=True))


def downgrade() -> None:
    op.drop_column("challenge_editions", "replay_day3_url")
    op.drop_column("challenge_editions", "replay_day2_url")
    op.drop_column("challenge_editions", "replay_day1_url")
    op.drop_column("challenge_editions", "closer_booking_url")
    op.drop_column("challenge_editions", "payment_url")
