"""Record which Claude quota stream produced each history sample.

Usage-API polls and inference-header observations quantize utilization
differently, so an interleaved series dips by a point between them. NULL marks
samples recorded before provenance was kept.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261006_000000_claude_quota_provenance"
down_revision = "20261004_010000_account_chart_color"
branch_labels = None
depends_on = None


def _columns(table: str) -> set[str]:
    return {str(column["name"]) for column in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    if "provenance" not in _columns("claude_quota_history"):
        op.add_column("claude_quota_history", sa.Column("provenance", sa.String(), nullable=True))


def downgrade() -> None:
    if "provenance" in _columns("claude_quota_history"):
        with op.batch_alter_table("claude_quota_history") as batch:
            batch.drop_column("provenance")
