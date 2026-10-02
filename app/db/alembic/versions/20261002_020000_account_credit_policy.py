"""Add the per-account purchased-credit policy.

``spend`` keeps the existing behaviour: spendable credits keep an account
routable after a quota window is exhausted. ``never`` makes exhausted windows
block the account even while upstream would bill credits instead of refusing.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261002_020000_account_credit_policy"
down_revision = "20261002_010000_request_logs_live_source_index"
branch_labels = None
depends_on = None


def _account_columns() -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns("accounts")}


def upgrade() -> None:
    if "credit_policy" in _account_columns():
        return
    with op.batch_alter_table("accounts") as batch_op:
        batch_op.add_column(sa.Column("credit_policy", sa.String(), server_default="spend", nullable=False))


def downgrade() -> None:
    if "credit_policy" not in _account_columns():
        return
    with op.batch_alter_table("accounts") as batch_op:
        batch_op.drop_column("credit_policy")
