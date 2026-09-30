"""Retain observed Claude reset deadlines without inventing historical cycles."""

import sqlalchemy as sa
from alembic import op

revision = "20260930_000000_claude_quota_deadlines"
down_revision = "20260929_040000_claude_usage_detail"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("claude_quota_history", sa.Column("resets_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("claude_quota_history") as batch:
        batch.drop_column("resets_at")
