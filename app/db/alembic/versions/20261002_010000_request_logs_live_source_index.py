"""Add the live-row partial index for the provider-source request-log facet.

The unfiltered request-log options walk each facet with a recursive skip scan
(``min(column) WHERE deleted_at IS NULL AND column > previous``). The other
facets got live-row partial indexes in
``20260909_130000_add_request_logs_live_facet_indexes``; the provider-source
facet came later and was served by ``idx_logs_model_source_time``, whose
probes walk soft-deleted rows because soft deletion keeps ``model_source_id``.
Built the same way: concurrently on PostgreSQL, replacing an invalid leftover
from an interrupted concurrent build.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261002_010000_request_logs_live_source_index"
down_revision = "20261002_000000_account_json_documents"
branch_labels = None
depends_on = None

_TABLE_NAME = "request_logs"
_INDEX_NAME = "idx_logs_model_source_live"
_COLUMNS_AND_PREDICATE = f"ON {_TABLE_NAME} (model_source_id) WHERE deleted_at IS NULL"


def upgrade() -> None:
    bind = op.get_bind()

    if bind.dialect.name == "postgresql":
        with op.get_context().autocommit_block():
            invalid = bind.execute(
                sa.text(
                    "SELECT 1 FROM pg_index i JOIN pg_class c ON c.oid = i.indexrelid "
                    "WHERE c.relname = :name AND NOT i.indisvalid"
                ),
                {"name": _INDEX_NAME},
            ).scalar()
            if invalid:
                op.execute(sa.text(f"DROP INDEX CONCURRENTLY IF EXISTS {_INDEX_NAME}"))
            op.execute(sa.text(f"CREATE INDEX CONCURRENTLY IF NOT EXISTS {_INDEX_NAME} {_COLUMNS_AND_PREDICATE}"))
        return

    op.execute(sa.text(f"CREATE INDEX IF NOT EXISTS {_INDEX_NAME} {_COLUMNS_AND_PREDICATE}"))


def downgrade() -> None:
    bind = op.get_bind()

    if bind.dialect.name == "postgresql":
        with op.get_context().autocommit_block():
            op.execute(sa.text(f"DROP INDEX CONCURRENTLY IF EXISTS {_INDEX_NAME}"))
        return

    op.drop_index(_INDEX_NAME, table_name=_TABLE_NAME, if_exists=True)
