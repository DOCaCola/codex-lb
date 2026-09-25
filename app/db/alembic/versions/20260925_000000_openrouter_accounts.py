"""Native OpenRouter account state and monitoring credentials."""

import sqlalchemy as sa
from alembic import op

revision = "20260925_000000_openrouter_accounts"
down_revision = "20260919_000000_merge_scim_overflow_heads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "openrouter_accounts",
        sa.Column("source_id", sa.String(), sa.ForeignKey("model_sources.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("management_key_encrypted", sa.LargeBinary(), nullable=True),
        sa.Column("state_json", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_table(
        "openrouter_cooldowns",
        sa.Column("source_id", sa.String(), sa.ForeignKey("model_sources.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("model", sa.String(), primary_key=True),
        sa.Column("until", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("openrouter_cooldowns")
    op.drop_table("openrouter_accounts")
