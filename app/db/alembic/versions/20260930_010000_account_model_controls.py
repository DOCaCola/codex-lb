"""Persist account model availability and OpenRouter routing priority."""

import sqlalchemy as sa
from alembic import op

revision = "20260930_010000_account_model_controls"
down_revision = "20260930_000000_claude_quota_deadlines"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("accounts", sa.Column("all_models", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("accounts", sa.Column("selected_models", sa.JSON(), nullable=False, server_default="[]"))
    op.add_column(
        "openrouter_accounts", sa.Column("routing_policy", sa.String(), nullable=False, server_default="normal")
    )


def downgrade() -> None:
    with op.batch_alter_table("openrouter_accounts") as batch:
        batch.drop_column("routing_policy")
    with op.batch_alter_table("accounts") as batch:
        batch.drop_column("selected_models")
        batch.drop_column("all_models")
