"""Attribute report history to model sources (Claude, OpenRouter, other providers).

Existing buckets get the NULL sentinel and the report coverage repair refolds
every retained raw hour with its source; pruned history stays unattributed.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261004_000000_report_rollup_model_source"
down_revision = "20261003_000000_claude_provider_account_uuid"
branch_labels = None
depends_on = None

_TABLE = "request_report_hourly_rollups"
_MERGE_TABLE = "request_report_hourly_rollups_merge"
_COLUMN = "model_source_id"
# Mirrors app.modules.accounts.usage_time_rollup.DIMENSION_SENTINEL (NULL).
_SENTINEL = "\x1f"
_KEYS = ("bucket_epoch", "account_id", "api_key_id", "model", "useragent_group", "conversation_id")
_MEASURES = (
    "request_count",
    "error_count",
    "cancelled_count",
    "input_tokens",
    "output_tokens",
    "reasoning_tokens",
    "reasoning_usage_known_requests",
    "cached_input_tokens",
    "cost_usd",
    "priced_requests",
    "unpriced_requests",
    "unmetered_requests",
    "coverage_unknown",
)


def _columns(table: str) -> set[str]:
    return {str(column["name"]) for column in sa.inspect(op.get_bind()).get_columns(table)}


def _replace_primary_key(columns: tuple[str, ...]) -> None:
    pk_name = sa.inspect(op.get_bind()).get_pk_constraint(_TABLE).get("name")
    with op.batch_alter_table(_TABLE) as batch:
        if pk_name:
            batch.drop_constraint(pk_name, type_="primary")
        batch.create_primary_key(pk_name or f"{_TABLE}_pkey", list(columns))


def upgrade() -> None:
    if _COLUMN in _columns(_TABLE):
        return
    with op.batch_alter_table(_TABLE) as batch:
        batch.add_column(sa.Column(_COLUMN, sa.String(), nullable=True))
    op.get_bind().execute(sa.text(f"UPDATE {_TABLE} SET {_COLUMN} = :sentinel"), {"sentinel": _SENTINEL})
    with op.batch_alter_table(_TABLE) as batch:
        batch.alter_column(_COLUMN, existing_type=sa.String(), nullable=False)
    _replace_primary_key((*_KEYS, _COLUMN))
    op.execute(
        sa.text(
            "UPDATE account_usage_rollup_state SET reports_coverage_repair_from = '1970-01-01 00:00:00' "
            "WHERE reports_folded_through > '1970-01-01 00:00:00'"
        )
    )


def downgrade() -> None:
    if _COLUMN not in _columns(_TABLE):
        return
    keys = ", ".join(_KEYS)
    measures = ", ".join(f"SUM({name}) AS {name}" for name in _MEASURES)
    columns = ", ".join((*_KEYS, "first_requested_at", *_MEASURES))
    # Sources of one key collapse into a single bucket before the key shrinks.
    op.execute(
        sa.text(
            f"CREATE TABLE {_MERGE_TABLE} AS SELECT {keys}, MIN(first_requested_at) AS first_requested_at, "
            f"{measures} FROM {_TABLE} GROUP BY {keys}"
        )
    )
    op.execute(sa.text(f"DELETE FROM {_TABLE}"))
    _replace_primary_key(_KEYS)
    with op.batch_alter_table(_TABLE) as batch:
        batch.drop_column(_COLUMN)
    op.execute(sa.text(f"INSERT INTO {_TABLE} ({columns}) SELECT {columns} FROM {_MERGE_TABLE}"))
    op.drop_table(_MERGE_TABLE)
