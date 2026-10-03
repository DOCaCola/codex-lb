"""Verified Anthropic account UUID for serving-account session metadata."""

import sqlalchemy as sa
from alembic import op

revision = "20261003_000000_claude_provider_account_uuid"
down_revision = "20261002_020000_account_credit_policy"
branch_labels = None
depends_on = None


def _columns(table: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(table):
        return set()
    return {str(column["name"]) for column in inspector.get_columns(table)}


def upgrade() -> None:
    # Existing accounts are re-verified against Anthropic on their next credential use.
    if "provider_account_uuid" not in _columns("claude_accounts"):
        with op.batch_alter_table("claude_accounts") as batch:
            batch.add_column(sa.Column("provider_account_uuid", sa.String(), nullable=True))


def downgrade() -> None:
    if "provider_account_uuid" in _columns("claude_accounts"):
        with op.batch_alter_table("claude_accounts") as batch:
            batch.drop_column("provider_account_uuid")
