"""Add OpenAI API accounts and share the pooled-account cooldown store.

Revision ID: 20261126_000000_openai_api_accounts
Revises: 20261120_010000_index_requested_models
"""

import sqlalchemy as sa
from alembic import op

revision = "20261126_000000_openai_api_accounts"
down_revision = "20261120_010000_index_requested_models"
branch_labels = None
depends_on = None

_ACCOUNTS_TABLE = "openai_api_accounts"
_LEGACY_COOLDOWNS_TABLE = "openrouter_cooldowns"
_COOLDOWNS_TABLE = "source_cooldowns"


def _rename_cooldowns(old: str, new: str) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table(old):
        return
    if inspector.has_table(new):
        # A chain replay over a current schema: the earlier revision recreated the old table empty.
        op.drop_table(old)
        return
    op.rename_table(old, new)
    if bind.dialect.name == "postgresql":
        # Postgres keeps constraint names across a table rename; name them after the table they now belong to.
        op.execute(f"ALTER TABLE {new} RENAME CONSTRAINT {old}_pkey TO {new}_pkey")
        op.execute(f"ALTER TABLE {new} RENAME CONSTRAINT {old}_source_id_fkey TO {new}_source_id_fkey")


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(_ACCOUNTS_TABLE):
        op.create_table(
            _ACCOUNTS_TABLE,
            sa.Column(
                "source_id", sa.String(), sa.ForeignKey("model_sources.id", ondelete="CASCADE"), primary_key=True
            ),
            sa.Column("routing_policy", sa.String(), nullable=False, server_default="normal"),
            sa.Column("state_json", sa.Text(), nullable=False),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        )
    _rename_cooldowns(_LEGACY_COOLDOWNS_TABLE, _COOLDOWNS_TABLE)


def downgrade() -> None:
    _rename_cooldowns(_COOLDOWNS_TABLE, _LEGACY_COOLDOWNS_TABLE)
    if sa.inspect(op.get_bind()).has_table(_ACCOUNTS_TABLE):
        op.drop_table(_ACCOUNTS_TABLE)
