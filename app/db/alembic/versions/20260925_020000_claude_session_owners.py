"""Durable account ownership for native Claude signed history."""

import sqlalchemy as sa
from alembic import op

revision = "20260925_020000_claude_session_owners"
down_revision = "20260925_010000_claude_accounts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "claude_session_owners",
        sa.Column("scope_hash", sa.String(), primary_key=True),
        sa.Column("source_id", sa.String(), sa.ForeignKey("model_sources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_claude_session_owners_expires_at", "claude_session_owners", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_claude_session_owners_expires_at", table_name="claude_session_owners")
    op.drop_table("claude_session_owners")
