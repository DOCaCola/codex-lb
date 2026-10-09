"""Drop the anonymous telemetry consent and identity columns.

This fork removed telemetry entirely; the consent decision, the random
instance id and the encrypted signing key are deleted with it. Downgrade
restores the columns empty (consent ``undecided``); the key is not recoverable.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261009_000000_drop_anonymous_telemetry"
down_revision = "20261006_000000_claude_quota_provenance"
branch_labels = None
depends_on = None

_COLUMNS = ("telemetry_consent", "telemetry_instance_id", "telemetry_private_key_encrypted")


def _columns() -> set[str]:
    return {str(column["name"]) for column in sa.inspect(op.get_bind()).get_columns("dashboard_settings")}


def upgrade() -> None:
    present = [name for name in _COLUMNS if name in _columns()]
    if present:
        with op.batch_alter_table("dashboard_settings") as batch:
            for name in present:
                batch.drop_column(name)


def downgrade() -> None:
    columns = _columns()
    with op.batch_alter_table("dashboard_settings") as batch:
        if "telemetry_consent" not in columns:
            batch.add_column(
                sa.Column(
                    "telemetry_consent",
                    sa.String(length=16),
                    server_default=sa.text("'undecided'"),
                    nullable=False,
                )
            )
        if "telemetry_instance_id" not in columns:
            batch.add_column(sa.Column("telemetry_instance_id", sa.String(length=36), nullable=True))
        if "telemetry_private_key_encrypted" not in columns:
            batch.add_column(sa.Column("telemetry_private_key_encrypted", sa.LargeBinary(), nullable=True))
