"""Operator note on Codex accounts and model sources. NULL means no note."""

import sqlalchemy as sa
from alembic import op

revision = "20261031_010000_account_notes"
down_revision = "20261031_000000_claude_plan_rename"
branch_labels = None
depends_on = None

_TABLES = ("accounts", "model_sources")
_COLUMN = "note"


def _has_column(table: str) -> bool:
    return _COLUMN in {str(column["name"]) for column in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    for table in _TABLES:
        if _has_column(table):
            continue
        with op.batch_alter_table(table) as batch:
            batch.add_column(sa.Column(_COLUMN, sa.Text(), nullable=True))


def downgrade() -> None:
    for table in _TABLES:
        if not _has_column(table):
            continue
        with op.batch_alter_table(table) as batch:
            batch.drop_column(_COLUMN)
