"""Authenticated Claude identity and generation-bound reconnect enrollment."""

import sqlalchemy as sa
from alembic import op

revision = "20260925_030000_claude_identity"
down_revision = "20260925_020000_claude_session_owners"
branch_labels = None
depends_on = None


def _columns(table: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(table):
        return set()
    return {str(column["name"]) for column in inspector.get_columns(table)}


def upgrade() -> None:
    if "identity_fingerprint" not in _columns("claude_accounts"):
        with op.batch_alter_table("claude_accounts") as batch:
            batch.add_column(sa.Column("identity_fingerprint", sa.String(), nullable=True))
            batch.create_unique_constraint("uq_claude_accounts_identity_fingerprint", ["identity_fingerprint"])
    if "source_id" not in _columns("claude_oauth_flows"):
        with op.batch_alter_table("claude_oauth_flows") as batch:
            batch.add_column(sa.Column("source_id", sa.String(), nullable=True))
            batch.add_column(sa.Column("generation", sa.Integer(), nullable=True))
            batch.create_foreign_key(
                "fk_claude_oauth_flows_source_id", "claude_accounts", ["source_id"], ["source_id"], ondelete="CASCADE"
            )


def downgrade() -> None:
    # Dropping a column drops its single-column constraints. They are not
    # dropped by name: a schema built from the models carries generated names.
    if "source_id" in _columns("claude_oauth_flows"):
        with op.batch_alter_table("claude_oauth_flows") as batch:
            batch.drop_column("generation")
            batch.drop_column("source_id")
    if "identity_fingerprint" in _columns("claude_accounts"):
        with op.batch_alter_table("claude_accounts") as batch:
            batch.drop_column("identity_fingerprint")
