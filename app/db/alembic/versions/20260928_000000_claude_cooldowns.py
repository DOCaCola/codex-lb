"""Persist model/account scoped Claude refusal deadlines."""

import sqlalchemy as sa
from alembic import op

revision = "20260928_000000_claude_cooldowns"
down_revision = "20260926_010000_claude_quota_history"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "claude_cooldowns",
        sa.Column(
            "source_id", sa.String(), sa.ForeignKey("claude_accounts.source_id", ondelete="CASCADE"), primary_key=True
        ),
        sa.Column("model", sa.String(), primary_key=True),
        sa.Column("until", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("claude_cooldowns")
