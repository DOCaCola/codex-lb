"""Remove per-selection OpenRouter context and output caps.

OpenRouter models now advertise their real provider limits; the Settings model
catalogue is the single place to lower a reported context window. The stored
caps are dropped and the catalog is marked stale so the OpenRouter scheduler
re-projects every selection with its real limits on its next pass.
"""

import json

import sqlalchemy as sa
from alembic import op

revision = "20261011_000000_openrouter_automatic_limits"
down_revision = "20261009_000000_drop_anonymous_telemetry"
branch_labels = None
depends_on = None

_REMOVED_KEYS = ("context_window", "max_output_tokens")


def upgrade() -> None:
    accounts = sa.table("openrouter_accounts", sa.column("source_id", sa.String()), sa.column("state_json", sa.Text()))
    connection = op.get_bind()
    for source_id, stored in connection.execute(sa.select(accounts.c.source_id, accounts.c.state_json)):
        state = json.loads(stored)
        state["selections"] = [
            {key: value for key, value in selection.items() if key not in _REMOVED_KEYS}
            for selection in state.get("selections", [])
        ]
        state["catalog_updated_at"] = None
        connection.execute(
            accounts.update().where(accounts.c.source_id == source_id).values(state_json=json.dumps(state))
        )


def downgrade() -> None:
    # Removed caps are not restored; older code applies its default cap on load.
    pass
