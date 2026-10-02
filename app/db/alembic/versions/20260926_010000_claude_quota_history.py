"""Persist successful Claude quota observations."""

import sqlalchemy as sa
from alembic import op

revision = "20260926_010000_claude_quota_history"
down_revision = "20260926_000000_quota_reset_webhook"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("claude_quota_history"):
        return
    op.create_table(
        "claude_quota_history",
        sa.Column(
            "source_id", sa.String(), sa.ForeignKey("claude_accounts.source_id", ondelete="CASCADE"), primary_key=True
        ),
        sa.Column("observed_at", sa.DateTime(), primary_key=True),
        sa.Column("window", sa.String(), primary_key=True),
        sa.Column("used_percent", sa.Float(), nullable=False),
    )


def downgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("claude_quota_history"):
        op.drop_table("claude_quota_history")
