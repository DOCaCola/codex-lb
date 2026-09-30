"""Persist native per-model reasoning eligibility."""

import sqlalchemy as sa
from alembic import op

revision = "20260930_020000_account_reasoning_policy"
down_revision = "20260930_010000_account_model_controls"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("accounts", sa.Column("reasoning_restrictions", sa.JSON(), nullable=False, server_default="{}"))


def downgrade() -> None:
    with op.batch_alter_table("accounts") as batch:
        batch.drop_column("reasoning_restrictions")
