"""Persist native per-model reasoning eligibility."""

import sqlalchemy as sa
from alembic import op

revision = "20260930_020000_account_reasoning_policy"
down_revision = "20260930_010000_account_model_controls"
branch_labels = None
depends_on = None


def _columns(table: str) -> set[str]:
    return {str(column["name"]) for column in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    if "reasoning_restrictions" not in _columns("accounts"):
        op.add_column("accounts", sa.Column("reasoning_restrictions", sa.JSON(), nullable=False, server_default="{}"))


def downgrade() -> None:
    if "reasoning_restrictions" in _columns("accounts"):
        with op.batch_alter_table("accounts") as batch:
            batch.drop_column("reasoning_restrictions")
