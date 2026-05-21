"""add provider_message_id to messages

Revision ID: 005
Revises: 004
Create Date: 2026-05-21
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("messages", sa.Column("provider_message_id", sa.String(length=128), nullable=True))
    op.create_index("ix_messages_provider_message_id", "messages", ["provider_message_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_messages_provider_message_id", table_name="messages")
    op.drop_column("messages", "provider_message_id")
