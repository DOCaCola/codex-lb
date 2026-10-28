"""Bind native Claude resource ownership to its authenticated identity."""

import sqlalchemy as sa
from alembic import op

revision = "20261028_000000_claude_resource_identity"
down_revision = "20261018_000000_model_compaction_routes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "claude_resource_origins",
        sa.Column("identity_generation", sa.Integer(), nullable=False, server_default="1"),
    )


def downgrade() -> None:
    with op.batch_alter_table("claude_resource_origins") as batch:
        batch.drop_column("identity_generation")
