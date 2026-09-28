"""Native resource origins independent of cache affinity."""

import sqlalchemy as sa
from alembic import op

revision = "20260929_000000_claude_resource_origins"
down_revision = "20260928_010000_claude_reset_grants"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "claude_resource_origins",
        sa.Column("resource_hash", sa.String(), primary_key=True),
        sa.Column("source_id", sa.String(), sa.ForeignKey("model_sources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_claude_resource_origins_expires_at", "claude_resource_origins", ["expires_at"])


def downgrade() -> None:
    op.drop_table("claude_resource_origins")
