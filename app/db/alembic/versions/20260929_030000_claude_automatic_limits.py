"""Remove manual Claude limits and add provider-local routing preference."""

import json

import sqlalchemy as sa
from alembic import op

revision = "20260929_030000_claude_automatic_limits"
down_revision = "20260929_020000_merge_upstream_routing_heads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("claude_accounts", sa.Column("routing_policy", sa.String(), nullable=False, server_default="normal"))
    accounts = sa.table("claude_accounts", sa.column("source_id", sa.String()), sa.column("state_json", sa.Text()))
    models = sa.table(
        "model_source_models",
        sa.column("source_id", sa.String()),
        sa.column("context_window", sa.Integer()),
        sa.column("max_output_tokens", sa.Integer()),
        sa.column("is_enabled", sa.Boolean()),
    )
    connection = op.get_bind()
    for source_id, stored in connection.execute(sa.select(accounts.c.source_id, accounts.c.state_json)):
        state = json.loads(stored)
        state["selections"] = [{"model": item["model"]} for item in state.get("selections", [])]
        state["catalog_updated_at"] = None
        state["catalog_requested_at"] = None
        connection.execute(
            accounts.update().where(accounts.c.source_id == source_id).values(state_json=json.dumps(state))
        )
        # Old projections contain operator budgets, not discovered capabilities.
        # The existing scheduler refreshes catalogs with no updated_at on its next pass.
        connection.execute(
            models.update()
            .where(models.c.source_id == source_id)
            .values(
                context_window=None,
                max_output_tokens=None,
                is_enabled=False,
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("claude_accounts") as batch:
        batch.drop_column("routing_policy")
