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


def upgrade() -> None:
    op.create_table(
        "model_redirects",
        sa.Column("source_model", sa.String(), primary_key=True),
        sa.Column("target_model", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.add_column("request_logs", sa.Column("requested_model", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("request_logs", "requested_model")
    op.drop_table("model_redirects")
