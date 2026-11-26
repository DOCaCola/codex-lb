"""Index redirected request-log model filters and facets.

Revision ID: 20261120_010000_index_requested_models
Revises: 20261120_000000_model_redirects
"""

import sqlalchemy as sa
from alembic import op

revision = "20261120_010000_index_requested_models"
down_revision = "20261120_000000_model_redirects"
branch_labels = None
depends_on = None

_INDEX = "idx_logs_requested_model_effort"
_PREDICATE = "requested_model IS NOT NULL"


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        with op.get_context().autocommit_block():
            invalid = bind.execute(
                sa.text(
                    "SELECT 1 FROM pg_index i JOIN pg_class c ON c.oid = i.indexrelid "
                    "WHERE c.relname = :name AND NOT i.indisvalid"
                ),
                {"name": _INDEX},
            ).scalar()
            if invalid:
                op.execute(sa.text(f"DROP INDEX CONCURRENTLY {_INDEX}"))
            op.execute(
                sa.text(
                    f"CREATE INDEX CONCURRENTLY IF NOT EXISTS {_INDEX} "
                    f"ON request_logs (requested_model, reasoning_effort) WHERE {_PREDICATE}"
                )
            )
        return
    op.create_index(
        _INDEX,
        "request_logs",
        ["requested_model", "reasoning_effort"],
        sqlite_where=sa.text(_PREDICATE),
        if_not_exists=True,
    )


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        with op.get_context().autocommit_block():
            op.execute(sa.text(f"DROP INDEX CONCURRENTLY IF EXISTS {_INDEX}"))
        return
    op.drop_index(_INDEX, table_name="request_logs", if_exists=True)
