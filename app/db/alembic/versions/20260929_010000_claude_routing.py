"""Provider-scoped routing target and admission recency."""

import sqlalchemy as sa
from alembic import op

revision = "20260929_010000_claude_routing"
down_revision = "20260929_000000_claude_resource_origins"
branch_labels = None
depends_on = None


def _columns(table: str) -> set[str]:
    return {str(column["name"]) for column in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    if "claude_single_account_id" not in _columns("dashboard_settings"):
        op.add_column("dashboard_settings", sa.Column("claude_single_account_id", sa.String(), nullable=True))
    if "last_selected_at" not in _columns("claude_accounts"):
        op.add_column("claude_accounts", sa.Column("last_selected_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    if "last_selected_at" in _columns("claude_accounts"):
        with op.batch_alter_table("claude_accounts") as batch:
            batch.drop_column("last_selected_at")
    if "claude_single_account_id" in _columns("dashboard_settings"):
        with op.batch_alter_table("dashboard_settings") as batch:
            batch.drop_column("claude_single_account_id")
