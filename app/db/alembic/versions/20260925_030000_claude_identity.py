"""Authenticated Claude identity and generation-bound reconnect enrollment."""

import sqlalchemy as sa
from alembic import op

revision = "20260925_030000_claude_identity"
down_revision = "20260925_020000_claude_session_owners"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("claude_accounts") as batch:
        batch.add_column(sa.Column("identity_fingerprint", sa.String(), nullable=True))
        batch.create_unique_constraint("uq_claude_accounts_identity_fingerprint", ["identity_fingerprint"])
    with op.batch_alter_table("claude_oauth_flows") as batch:
        batch.add_column(sa.Column("source_id", sa.String(), nullable=True))
        batch.add_column(sa.Column("generation", sa.Integer(), nullable=True))
        batch.create_foreign_key(
            "fk_claude_oauth_flows_source_id", "claude_accounts", ["source_id"], ["source_id"], ondelete="CASCADE"
        )


def downgrade() -> None:
    with op.batch_alter_table("claude_oauth_flows") as batch:
        batch.drop_constraint("fk_claude_oauth_flows_source_id", type_="foreignkey")
        batch.drop_column("generation")
        batch.drop_column("source_id")
    with op.batch_alter_table("claude_accounts") as batch:
        batch.drop_constraint("uq_claude_accounts_identity_fingerprint", type_="unique")
        batch.drop_column("identity_fingerprint")
