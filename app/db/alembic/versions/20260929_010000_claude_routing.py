"""Provider-scoped routing target and admission recency."""

import sqlalchemy as sa
from alembic import op

revision = "20260929_010000_claude_routing"
down_revision = "20260929_000000_claude_resource_origins"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("dashboard_settings", sa.Column("claude_single_account_id", sa.String(), nullable=True))
    op.add_column("claude_accounts", sa.Column("last_selected_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("claude_accounts") as batch:
        batch.drop_column("last_selected_at")
    with op.batch_alter_table("dashboard_settings") as batch:
        batch.drop_column("claude_single_account_id")
