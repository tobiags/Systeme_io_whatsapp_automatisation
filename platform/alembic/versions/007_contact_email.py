"""add email column to contacts

Revision ID: 007
Revises: 006
Create Date: 2026-05-30
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("contacts", sa.Column("email", sa.String(length=256), nullable=True))
    op.create_index("ix_contacts_email", "contacts", ["email"])


def downgrade() -> None:
    op.drop_index("ix_contacts_email", table_name="contacts")
    op.drop_column("contacts", "email")
