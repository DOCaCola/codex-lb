"""Claude profile labels and reconnects held for identity confirmation."""

import sqlalchemy as sa
from alembic import op

revision = "20261031_020000_claude_pending_reconnects"
down_revision = "20261031_010000_account_notes"
branch_labels = None
depends_on = None

_LABELS = ("account_email", "organization_name")
_TABLE = "claude_pending_reconnects"


def _columns() -> set[str]:
    return {str(column["name"]) for column in sa.inspect(op.get_bind()).get_columns("claude_accounts")}


def upgrade() -> None:
    missing = [name for name in _LABELS if name not in _columns()]
    if missing:
        with op.batch_alter_table("claude_accounts") as batch:
            for name in missing:
                batch.add_column(sa.Column(name, sa.String(), nullable=True))
    if not sa.inspect(op.get_bind()).has_table(_TABLE):
        op.create_table(
            _TABLE,
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column(
                "source_id",
                sa.String(),
                sa.ForeignKey("claude_accounts.source_id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("generation", sa.Integer(), nullable=False),
            sa.Column("identity_fingerprint", sa.String(), nullable=False),
            sa.Column("credentials_encrypted", sa.LargeBinary(), nullable=False),
            sa.Column("subscription_json", sa.Text(), nullable=True),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_claude_pending_reconnects_source_id", _TABLE, ["source_id"])


def downgrade() -> None:
    if sa.inspect(op.get_bind()).has_table(_TABLE):
        op.drop_table(_TABLE)
    present = [name for name in _LABELS if name in _columns()]
    if present:
        with op.batch_alter_table("claude_accounts") as batch:
            for name in present:
                batch.drop_column(name)
