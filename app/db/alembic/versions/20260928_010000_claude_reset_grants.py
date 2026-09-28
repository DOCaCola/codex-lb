"""Durable Claude reset intent and selective cooldown evidence."""

import sqlalchemy as sa
from alembic import op

revision = "20260928_010000_claude_reset_grants"
down_revision = "20260928_000000_claude_cooldowns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("claude_cooldowns", sa.Column("evidence_json", sa.Text(), nullable=True))
    op.create_table(
        "claude_reset_operations",
        sa.Column("operation_id", sa.String(), primary_key=True),
        sa.Column("source_id", sa.String(), nullable=False),
        sa.Column("identity", sa.String(), nullable=False),
        sa.Column("grant_id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("lease_until", sa.DateTime(), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("result_json", sa.Text(), nullable=True),
    )
    op.create_index("ix_claude_reset_operations_identity", "claude_reset_operations", ["identity"])


def downgrade() -> None:
    op.drop_table("claude_reset_operations")
    with op.batch_alter_table("claude_cooldowns") as batch:
        batch.drop_column("evidence_json")
