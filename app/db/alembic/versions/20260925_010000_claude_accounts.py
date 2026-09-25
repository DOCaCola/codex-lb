"""Claude credentials, single-use OAuth flows and shared version state."""

import sqlalchemy as sa
from alembic import op

revision = "20260925_010000_claude_accounts"
down_revision = "20260925_000000_openrouter_accounts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "claude_accounts",
        sa.Column("source_id", sa.String(), sa.ForeignKey("model_sources.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("credentials_encrypted", sa.LargeBinary(), nullable=False),
        sa.Column("grant_fingerprint", sa.String(), unique=True, nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("credential_status", sa.String(), nullable=False, server_default="ready"),
        sa.Column("generation", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("refresh_intent", sa.String(), nullable=True),
        sa.Column("refresh_started_at", sa.DateTime(), nullable=True),
        sa.Column("retry_at", sa.DateTime(), nullable=True),
        sa.Column("state_json", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_table(
        "claude_oauth_flows",
        sa.Column("state_hash", sa.String(), primary_key=True),
        sa.Column("verifier_encrypted", sa.LargeBinary(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "claude_version_state",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("discovered_version", sa.String(), nullable=False),
        sa.Column("pinned_version", sa.String(), nullable=True),
        sa.Column("last_checked_at", sa.DateTime(), nullable=True),
        sa.Column("last_changed_at", sa.DateTime(), nullable=True),
        sa.Column("retry_at", sa.DateTime(), nullable=True),
        sa.Column("etag", sa.String(), nullable=True),
        sa.Column("error", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("claude_version_state")
    op.drop_table("claude_oauth_flows")
    op.drop_table("claude_accounts")
