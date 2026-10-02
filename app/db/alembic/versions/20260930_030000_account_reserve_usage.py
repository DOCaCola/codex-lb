"""Retain the latest account-bound Luna Reserve usage observation."""

import sqlalchemy as sa
from alembic import op

revision = "20260930_030000_account_reserve_usage"
down_revision = "20260930_020000_account_reasoning_policy"
branch_labels = None
depends_on = None


def _columns(table: str) -> set[str]:
    return {str(column["name"]) for column in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    if "reserve_usage" not in _columns("accounts"):
        op.add_column("accounts", sa.Column("reserve_usage", sa.JSON(), nullable=True))


def downgrade() -> None:
    if "reserve_usage" in _columns("accounts"):
        with op.batch_alter_table("accounts") as batch:
            batch.drop_column("reserve_usage")
