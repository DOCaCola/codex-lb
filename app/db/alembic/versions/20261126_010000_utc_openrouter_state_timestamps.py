"""Store OpenRouter account observation times as UTC with an explicit offset.

The catalog, key and credit observation times were written as naive UTC, so the
dashboard read them as browser-local time. Account state now requires aware
timestamps; stored naive values are rewritten as UTC.

Revision ID: 20261126_010000_utc_openrouter_state_timestamps
Revises: 20261126_000000_openai_api_accounts
"""

import json
from collections.abc import Callable
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

revision = "20261126_010000_utc_openrouter_state_timestamps"
down_revision = "20261126_000000_openai_api_accounts"
branch_labels = None
depends_on = None

_TIMESTAMP_KEYS = ("catalog_updated_at", "key_updated_at", "credits_updated_at")


def _to_utc(value: datetime) -> str:
    aware = value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
    return aware.isoformat().replace("+00:00", "Z")


def _to_naive_utc(value: datetime) -> str:
    return (value if value.tzinfo is None else value.astimezone(UTC).replace(tzinfo=None)).isoformat()


def _rewrite(convert: Callable[[datetime], str]) -> None:
    accounts = sa.table("openrouter_accounts", sa.column("source_id", sa.String()), sa.column("state_json", sa.Text()))
    connection = op.get_bind()
    for source_id, stored in connection.execute(sa.select(accounts.c.source_id, accounts.c.state_json)):
        state = json.loads(stored)
        for key in _TIMESTAMP_KEYS:
            if state.get(key) is not None:
                state[key] = convert(datetime.fromisoformat(state[key]))
        connection.execute(
            accounts.update().where(accounts.c.source_id == source_id).values(state_json=json.dumps(state))
        )


def upgrade() -> None:
    _rewrite(_to_utc)


def downgrade() -> None:
    # Older code compares these values with naive UTC.
    _rewrite(_to_naive_utc)
