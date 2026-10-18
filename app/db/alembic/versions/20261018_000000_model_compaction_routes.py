"""dashboard-managed native compaction model routes

Revision ID: 20261018_000000_model_compaction_routes
Revises: 20261017_000000_drop_downstream_websocket_idle_timeout
Create Date: 2026-10-18

Adds ``model_compaction_routes``: one row per native coding model whose
compaction requests run on another native model, optionally at another
reasoning effort.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20261018_000000_model_compaction_routes"
down_revision = "20261017_000000_drop_downstream_websocket_idle_timeout"
branch_labels = None
depends_on = None

_TABLE = "model_compaction_routes"


def upgrade() -> None:
    bind = op.get_bind()
    if sa.inspect(bind).has_table(_TABLE):
        return
    op.create_table(
        _TABLE,
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("compaction_model", sa.String(), nullable=False),
        sa.Column("reasoning_effort", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("slug"),
    )


def downgrade() -> None:
    bind = op.get_bind()
    if sa.inspect(bind).has_table(_TABLE):
        op.drop_table(_TABLE)
