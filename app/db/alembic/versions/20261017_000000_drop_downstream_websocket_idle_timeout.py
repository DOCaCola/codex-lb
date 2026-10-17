"""Drop the dashboard downstream WebSocket idle timeout.

Client Responses WebSockets are no longer closed on a timer: an idle socket is
reclaimed only when the WebSocket admission lane is full, so the
``proxy_downstream_websocket_idle_timeout_seconds`` override has no consumer.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261017_000000_drop_downstream_websocket_idle_timeout"
down_revision = "20261014_000000_request_log_upstream_terminal_latency"
branch_labels = None
depends_on = None

_TABLE = "dashboard_settings"
_COLUMN = "proxy_downstream_websocket_idle_timeout_seconds"


def _columns() -> set[str]:
    return {str(column["name"]) for column in sa.inspect(op.get_bind()).get_columns(_TABLE)}


def upgrade() -> None:
    if _COLUMN in _columns():
        with op.batch_alter_table(_TABLE) as batch:
            batch.drop_column(_COLUMN)


def downgrade() -> None:
    if _COLUMN not in _columns():
        op.add_column(_TABLE, sa.Column(_COLUMN, sa.Float(), nullable=True))
