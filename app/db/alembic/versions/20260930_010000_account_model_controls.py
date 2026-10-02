"""Persist account model availability and OpenRouter routing priority."""

import sqlalchemy as sa
from alembic import op

revision = "20260930_010000_account_model_controls"
down_revision = "20260930_000000_claude_quota_deadlines"
branch_labels = None
depends_on = None


def _columns(table: str) -> set[str]:
    return {str(column["name"]) for column in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    account_columns = _columns("accounts")
    if "all_models" not in account_columns:
        op.add_column("accounts", sa.Column("all_models", sa.Boolean(), nullable=False, server_default=sa.true()))
    if "selected_models" not in account_columns:
        op.add_column("accounts", sa.Column("selected_models", sa.JSON(), nullable=False, server_default="[]"))
    if "routing_policy" not in _columns("openrouter_accounts"):
        op.add_column(
            "openrouter_accounts", sa.Column("routing_policy", sa.String(), nullable=False, server_default="normal")
        )


def downgrade() -> None:
    if "routing_policy" in _columns("openrouter_accounts"):
        with op.batch_alter_table("openrouter_accounts") as batch:
            batch.drop_column("routing_policy")
    account_columns = _columns("accounts")
    with op.batch_alter_table("accounts") as batch:
        for name in ("selected_models", "all_models"):
            if name in account_columns:
                batch.drop_column(name)
