"""Add UNIQUE constraint on audit_events.aggregate_id to prevent race-condition double-sends.

Revision ID: 010
Revises: 009
Create Date: 2026-06-08
"""
from alembic import op

revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Remove any duplicates that may have been inserted before this migration
    # (keeps the earliest record for each aggregate_id).
    op.execute("""
        DELETE FROM audit_events
        WHERE id NOT IN (
            SELECT MIN(id)
            FROM audit_events
            GROUP BY aggregate_id
        )
    """)
    op.create_unique_constraint(
        "uq_audit_events_aggregate_id",
        "audit_events",
        ["aggregate_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_audit_events_aggregate_id", "audit_events", type_="unique")
