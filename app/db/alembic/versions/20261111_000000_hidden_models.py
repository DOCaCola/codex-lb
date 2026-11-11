"""models hidden from client model lists

Revision ID: 20261111_000000_hidden_models
Revises: 20261101_000000_claude_client_builds
Create Date: 2026-11-11

Adds ``hidden_models``: one row per model slug the operator hid from client
model lists. Hidden models stay usable by name.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20261111_000000_hidden_models"
down_revision = "20261101_000000_claude_client_builds"
branch_labels = None
depends_on = None

_TABLE = "hidden_models"


def upgrade() -> None:
    bind = op.get_bind()
    if sa.inspect(bind).has_table(_TABLE):
        return
    op.create_table(
        _TABLE,
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("slug"),
    )


def downgrade() -> None:
    bind = op.get_bind()
    if sa.inspect(bind).has_table(_TABLE):
        op.drop_table(_TABLE)
