"""Retain ingress operations independently of workload kinds."""

import sqlalchemy as sa
from alembic import op

revision = "20261001_000000_request_operation"
down_revision = "20260930_030000_account_reserve_usage"
branch_labels = None
depends_on = None


def _columns(table: str) -> set[str]:
    return {str(column["name"]) for column in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    if "request_operation" not in _columns("request_logs"):
        op.add_column("request_logs", sa.Column("request_operation", sa.String(), nullable=True))


def downgrade() -> None:
    if "request_operation" in _columns("request_logs"):
        with op.batch_alter_table("request_logs") as batch:
            batch.drop_column("request_operation")
