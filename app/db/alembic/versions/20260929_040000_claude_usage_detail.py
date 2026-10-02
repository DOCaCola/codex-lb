"""Preserve reported cache-write and upstream thinking detail without historical guesses."""

import sqlalchemy as sa
from alembic import op

revision = "20260929_040000_claude_usage_detail"
down_revision = "20260929_030000_claude_automatic_limits"
branch_labels = None
depends_on = None

_REQUEST_LOG_COLUMNS: tuple[tuple[str, type[sa.types.TypeEngine]], ...] = (
    ("cache_creation_tokens", sa.Integer),
    ("cache_creation_5m_tokens", sa.Integer),
    ("cache_creation_1h_tokens", sa.Integer),
    ("upstream_thinking_budget_tokens", sa.Integer),
    ("upstream_thinking_mode", sa.String),
    ("upstream_reasoning_effort", sa.String),
    ("cost_provenance", sa.String),
)
_ROLLUP_TABLES = (
    "account_usage_rollups",
    "api_key_usage_rollups",
    "request_usage_hourly_rollups",
    "request_demand_quarter_rollups",
    "request_report_hourly_rollups",
)
_REPAIRED_ROLLUP_TABLES = ("account_usage_rollups", "api_key_usage_rollups")
_COUNT_COLUMNS = ("priced_requests", "unpriced_requests", "unmetered_requests")


def _columns(table: str) -> set[str]:
    return {str(column["name"]) for column in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    request_log_columns = _columns("request_logs")
    for name, column_type in _REQUEST_LOG_COLUMNS:
        if name not in request_log_columns:
            op.add_column("request_logs", sa.Column(name, column_type(), nullable=True))
    # The re-fold requests belong to the coverage columns' introduction; a
    # schema that already carries them has already folded with coverage.
    if "reports_coverage_repair_from" not in _columns("account_usage_rollup_state"):
        op.add_column(
            "account_usage_rollup_state", sa.Column("reports_coverage_repair_from", sa.DateTime(), nullable=True)
        )
        op.execute(
            sa.text(
                "UPDATE account_usage_rollup_state SET reports_coverage_repair_from = '1970-01-01 00:00:00' "
                "WHERE reports_folded_through > '1970-01-01 00:00:00'"
            )
        )
        op.execute(
            sa.text(
                "UPDATE account_usage_rollup_state SET upgrade_repair_from = '1970-01-01 00:00:00' "
                "WHERE hourly_folded_through > '1970-01-01 00:00:00'"
            )
        )
    for table in _ROLLUP_TABLES:
        rollup_columns = _columns(table)
        for name in _COUNT_COLUMNS:
            if name not in rollup_columns:
                op.add_column(table, sa.Column(name, sa.BigInteger(), nullable=False, server_default="0"))
        if "coverage_unknown" not in rollup_columns:
            op.add_column(table, sa.Column("coverage_unknown", sa.BigInteger(), nullable=False, server_default="0"))
            # Existing aggregates can outlive their raw rows. A zero initialized
            # count must not assert complete historical coverage.
            op.execute(sa.text(f"UPDATE {table} SET coverage_unknown = 1"))
        if table in _REPAIRED_ROLLUP_TABLES and "coverage_repair_attempted" not in rollup_columns:
            op.add_column(
                table,
                sa.Column("coverage_repair_attempted", sa.Boolean(), nullable=False, server_default=sa.false()),
            )


def downgrade() -> None:
    if "reports_coverage_repair_from" in _columns("account_usage_rollup_state"):
        with op.batch_alter_table("account_usage_rollup_state") as batch:
            batch.drop_column("reports_coverage_repair_from")
    for table in reversed(_ROLLUP_TABLES):
        rollup_columns = _columns(table)
        added = ("coverage_repair_attempted", "coverage_unknown", *reversed(_COUNT_COLUMNS))
        with op.batch_alter_table(table) as batch:
            for name in added:
                if name in rollup_columns:
                    batch.drop_column(name)
    request_log_columns = _columns("request_logs")
    with op.batch_alter_table("request_logs") as batch:
        for name, _column_type in reversed(_REQUEST_LOG_COLUMNS):
            if name in request_log_columns:
                batch.drop_column(name)
