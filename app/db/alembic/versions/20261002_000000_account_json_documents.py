"""Store account JSON documents as PostgreSQL jsonb.

PostgreSQL ``json`` has no equality operator. Alembic compares a column's
server default by evaluating ``reflected = declared`` on the server, so the
``json`` defaults of ``selected_models`` and ``reasoning_restrictions`` made
every schema drift check fail. ``jsonb`` compares by value. ``reserve_usage``
moves with them so the account documents share one storage type. SQLite keeps
its text-backed JSON, which needs no change.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "20261002_000000_account_json_documents"
down_revision = "20261001_000000_request_operation"
branch_labels = None
depends_on = None

_TABLE = "accounts"
_DOCUMENTS: tuple[tuple[str, str | None], ...] = (
    ("selected_models", "'[]'"),
    ("reasoning_restrictions", "'{}'"),
    ("reserve_usage", None),
)


def _convert(*, to_jsonb: bool) -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    reflected = {str(column["name"]): column["type"] for column in sa.inspect(bind).get_columns(_TABLE)}
    target = "jsonb" if to_jsonb else "json"
    for name, default in _DOCUMENTS:
        if isinstance(reflected[name], JSONB) == to_jsonb:
            continue
        clauses = [f"ALTER COLUMN {name} TYPE {target} USING {name}::{target}"]
        if default is not None:
            clauses = [
                f"ALTER COLUMN {name} DROP DEFAULT",
                *clauses,
                f"ALTER COLUMN {name} SET DEFAULT {default}::{target}",
            ]
        op.execute(sa.text(f"ALTER TABLE {_TABLE} {', '.join(clauses)}"))


def upgrade() -> None:
    _convert(to_jsonb=True)


def downgrade() -> None:
    _convert(to_jsonb=False)
