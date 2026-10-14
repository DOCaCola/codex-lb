"""Persist the upstream-terminal latency that bounds a request's generation window.

``latency_ms`` runs until the request log is written, after downstream delivery
and settlement bookkeeping. Throughput divides output by the span from first
token to the upstream terminal frame, so that instant is stored separately.
Historical rows stay NULL: no terminal instant was observed for them.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261014_000000_request_log_upstream_terminal_latency"
down_revision = "20261011_010000_hourly_rollup_model_source_kind"
branch_labels = None
depends_on = None

_COLUMN = "latency_upstream_terminal_ms"


def _columns() -> set[str]:
    return {str(column["name"]) for column in sa.inspect(op.get_bind()).get_columns("request_logs")}


def upgrade() -> None:
    if _COLUMN not in _columns():
        op.add_column("request_logs", sa.Column(_COLUMN, sa.Integer(), nullable=True))


def downgrade() -> None:
    if _COLUMN in _columns():
        with op.batch_alter_table("request_logs") as batch:
            batch.drop_column(_COLUMN)
