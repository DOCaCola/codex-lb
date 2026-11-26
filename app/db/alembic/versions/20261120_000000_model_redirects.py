"""Store model redirects and their request-log attribution.

Revision ID: 20261120_000000_model_redirects
Revises: 20261111_000000_hidden_models
"""

import sqlalchemy as sa
from alembic import op

revision = "20261120_000000_model_redirects"
down_revision = "20261111_000000_hidden_models"
branch_labels = None
depends_on = None

_REDIRECTS_TABLE = "model_redirects"
_REQUEST_LOGS_TABLE = "request_logs"
_REQUESTED_MODEL_COLUMN = "requested_model"


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(_REDIRECTS_TABLE):
        op.create_table(
            _REDIRECTS_TABLE,
            sa.Column("source_model", sa.String(), primary_key=True),
            sa.Column("target_model", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        )
    if _REQUESTED_MODEL_COLUMN not in {column["name"] for column in inspector.get_columns(_REQUEST_LOGS_TABLE)}:
        op.add_column(_REQUEST_LOGS_TABLE, sa.Column(_REQUESTED_MODEL_COLUMN, sa.String(), nullable=True))


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if _REQUESTED_MODEL_COLUMN in {column["name"] for column in inspector.get_columns(_REQUEST_LOGS_TABLE)}:
        op.drop_column(_REQUEST_LOGS_TABLE, _REQUESTED_MODEL_COLUMN)
    if inspector.has_table(_REDIRECTS_TABLE):
        op.drop_table(_REDIRECTS_TABLE)
