"""Retain the latest account-bound Luna Reserve usage observation."""

import sqlalchemy as sa
from alembic import op

revision = "20260930_030000_account_reserve_usage"
down_revision = "20260930_020000_account_reasoning_policy"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("accounts", sa.Column("reserve_usage", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("accounts") as batch:
        batch.drop_column("reserve_usage")
