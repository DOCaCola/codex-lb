"""Attribute hourly usage history to model-source kinds (Codex, Claude, OpenRouter, ...).

Existing buckets get the NULL sentinel and the post-upgrade repair refolds every
retained raw hour with its kind; pruned history stays attributed to Codex.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261011_010000_hourly_rollup_model_source_kind"
down_revision = "20261011_000000_openrouter_automatic_limits"
branch_labels = None
depends_on = None

_TABLE = "request_usage_hourly_rollups"
_MERGE_TABLE = "request_usage_hourly_rollups_merge"
_COLUMN = "model_source_kind"
# Mirrors app.modules.accounts.usage_time_rollup.DIMENSION_SENTINEL (NULL).
_SENTINEL = "\x1f"
_KEYS = ("bucket_epoch", "account_id", "api_key_id", "model", "service_tier", "request_kind", "is_deleted")
_MEASURES = (
    "request_count",
    "error_count",
    "cancelled_count",
    "input_tokens",
    "output_tokens",
    "reasoning_tokens",
    "output_or_reasoning_tokens",
    "cached_input_tokens",
    "cached_input_tokens_clamped",
    "cost_usd",
    "cost_count",
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
            "UPDATE account_usage_rollup_state SET upgrade_repair_from = '1970-01-01 00:00:00' "
            "WHERE hourly_folded_through > '1970-01-01 00:00:00'"
        )
    )


def downgrade() -> None:
    if _COLUMN not in _columns(_TABLE):
        return
    keys = ", ".join(_KEYS)
    measures = ", ".join(f"SUM({name}) AS {name}" for name in _MEASURES)
    columns = ", ".join((*_KEYS, *_MEASURES))
    # Kinds of one key collapse into a single bucket before the key shrinks.
    op.execute(sa.text(f"CREATE TABLE {_MERGE_TABLE} AS SELECT {keys}, {measures} FROM {_TABLE} GROUP BY {keys}"))
    op.execute(sa.text(f"DELETE FROM {_TABLE}"))
    _replace_primary_key(_KEYS)
    with op.batch_alter_table(_TABLE) as batch:
        batch.drop_column(_COLUMN)
    op.execute(sa.text(f"INSERT INTO {_TABLE} ({columns}) SELECT {columns} FROM {_MERGE_TABLE}"))
    op.drop_table(_MERGE_TABLE)
