"""Preserve reported cache-write and upstream thinking detail without historical guesses."""

import sqlalchemy as sa
from alembic import op

revision = "20260929_040000_claude_usage_detail"
down_revision = "20260929_030000_claude_automatic_limits"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for name in (
        "cache_creation_tokens",
        "cache_creation_5m_tokens",
        "cache_creation_1h_tokens",
        "upstream_thinking_budget_tokens",
    ):
        op.add_column("request_logs", sa.Column(name, sa.Integer(), nullable=True))
    op.add_column("request_logs", sa.Column("upstream_thinking_mode", sa.String(), nullable=True))
    op.add_column("request_logs", sa.Column("upstream_reasoning_effort", sa.String(), nullable=True))
    op.add_column("request_logs", sa.Column("cost_provenance", sa.String(), nullable=True))
    op.add_column("account_usage_rollup_state", sa.Column("reports_coverage_repair_from", sa.DateTime(), nullable=True))
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
    for table in (
        "account_usage_rollups",
        "api_key_usage_rollups",
        "request_usage_hourly_rollups",
        "request_demand_quarter_rollups",
        "request_report_hourly_rollups",
    ):
        for name in ("priced_requests", "unpriced_requests", "unmetered_requests"):
            op.add_column(table, sa.Column(name, sa.BigInteger(), nullable=False, server_default="0"))
        op.add_column(table, sa.Column("coverage_unknown", sa.BigInteger(), nullable=False, server_default="0"))
        # Existing aggregates can outlive their raw rows. A zero initialized
        # count must not assert complete historical coverage.
        op.execute(sa.text(f"UPDATE {table} SET coverage_unknown = 1"))
    for table in ("account_usage_rollups", "api_key_usage_rollups"):
        op.add_column(
            table,
            sa.Column("coverage_repair_attempted", sa.Boolean(), nullable=False, server_default=sa.false()),
        )


def downgrade() -> None:
    with op.batch_alter_table("account_usage_rollup_state") as batch:
        batch.drop_column("reports_coverage_repair_from")
    for table in (
        "request_report_hourly_rollups",
        "request_demand_quarter_rollups",
        "request_usage_hourly_rollups",
        "api_key_usage_rollups",
        "account_usage_rollups",
    ):
        with op.batch_alter_table(table) as batch:
            if table in ("account_usage_rollups", "api_key_usage_rollups"):
                batch.drop_column("coverage_repair_attempted")
            batch.drop_column("coverage_unknown")
            batch.drop_column("unmetered_requests")
            batch.drop_column("unpriced_requests")
            batch.drop_column("priced_requests")
    with op.batch_alter_table("request_logs") as batch:
        batch.drop_column("cost_provenance")
        batch.drop_column("upstream_thinking_mode")
        batch.drop_column("upstream_reasoning_effort")
        for name in (
            "upstream_thinking_budget_tokens",
            "cache_creation_1h_tokens",
            "cache_creation_5m_tokens",
            "cache_creation_tokens",
        ):
            batch.drop_column(name)
