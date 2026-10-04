"""Operator-picked chart colour for Codex accounts and model sources.

NULL keeps the account on automatic palette assignment.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261004_010000_account_chart_color"
down_revision = "20261004_000000_report_rollup_model_source"
branch_labels = None
depends_on = None

_TABLES = ("accounts", "model_sources")
_COLUMN = "chart_color"


def _has_column(table: str) -> bool:
    return _COLUMN in {str(column["name"]) for column in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    for table in _TABLES:
        if _has_column(table):
            continue
        with op.batch_alter_table(table) as batch:
            batch.add_column(sa.Column(_COLUMN, sa.Integer(), nullable=True))


def downgrade() -> None:
    for table in _TABLES:
        if not _has_column(table):
            continue
        with op.batch_alter_table(table) as batch:
            batch.drop_column(_COLUMN)
