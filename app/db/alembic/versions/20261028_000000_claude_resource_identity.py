"""Bind native Claude resource ownership to its authenticated identity."""

import sqlalchemy as sa
from alembic import op

revision = "20261028_000000_claude_resource_identity"
down_revision = "20261018_000000_model_compaction_routes"
branch_labels = None
depends_on = None

_TABLE = "claude_resource_origins"
_COLUMN = "identity_generation"


def _has_column() -> bool:
    return _COLUMN in {str(column["name"]) for column in sa.inspect(op.get_bind()).get_columns(_TABLE)}


def upgrade() -> None:
    if _has_column():
        return
    op.add_column(_TABLE, sa.Column(_COLUMN, sa.Integer(), nullable=False, server_default="1"))


def downgrade() -> None:
    if not _has_column():
        return
    with op.batch_alter_table(_TABLE) as batch:
        batch.drop_column(_COLUMN)
