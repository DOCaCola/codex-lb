"""Durable quota reset observations and webhook delivery."""

import sqlalchemy as sa
from alembic import op

revision = "20260926_000000_quota_reset_webhook"
down_revision = "20260925_030000_claude_identity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "quota_webhook_config",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("kinds", sa.Text(), nullable=False),
        sa.Column("url_encrypted", sa.LargeBinary()),
        sa.Column("secret_encrypted", sa.LargeBinary()),
        sa.Column("generation", sa.Integer(), nullable=False),
        sa.Column("changed_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "quota_webhook_baselines",
        sa.Column("account_id", sa.String(), sa.ForeignKey("accounts.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("window", sa.String(), primary_key=True),
        sa.Column("identity", sa.Text(), nullable=False),
        sa.Column("snapshot", sa.Text(), nullable=False),
        sa.Column("observed_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "quota_webhook_deliveries",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("generation", sa.Integer(), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("next_at", sa.DateTime(), nullable=False),
        sa.Column("lease_id", sa.String()),
        sa.Column("lease_until", sa.DateTime()),
        sa.Column("last_http_status", sa.Integer()),
        sa.Column("last_error", sa.String()),
    )
    op.create_index("ix_quota_webhook_deliveries_next_at", "quota_webhook_deliveries", ["next_at"])
    op.create_table(
        "quota_webhook_redemptions",
        sa.Column("upstream_account_id", sa.String(), primary_key=True),
        sa.Column("suppress_until", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("quota_webhook_redemptions")
    op.drop_table("quota_webhook_deliveries")
    op.drop_table("quota_webhook_baselines")
    op.drop_table("quota_webhook_config")
