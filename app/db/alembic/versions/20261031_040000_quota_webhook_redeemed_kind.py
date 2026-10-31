"""Quota webhook: report reset-credit redemptions as their own event kind.

The redemption marker becomes the redemption time instead of a suppression
deadline. Configurations that received unexpected resets also receive the new
redeemed kind, because those events were previously delivered as unexpected.
"""

import json

import sqlalchemy as sa
from alembic import op

revision = "20261031_040000_quota_webhook_redeemed_kind"
down_revision = "20261031_030000_account_subscription_ends"
branch_labels = None
depends_on = None

_TABLE = "quota_webhook_redemptions"


def _columns() -> set[str]:
    return {str(column["name"]) for column in sa.inspect(op.get_bind()).get_columns(_TABLE)}


def _rewrite_kinds(change) -> None:
    bind = op.get_bind()
    for row_id, kinds in bind.execute(sa.text("SELECT id, kinds FROM quota_webhook_config")).all():
        updated = change(json.loads(kinds))
        bind.execute(
            sa.text("UPDATE quota_webhook_config SET kinds = :kinds WHERE id = :id"),
            {"kinds": json.dumps(updated, separators=(",", ":")), "id": row_id},
        )


def upgrade() -> None:
    if "suppress_until" in _columns():
        # Rows hold short-lived markers; dropping them loses at most the
        # labelling of a redemption made just before this upgrade.
        op.execute(sa.text(f"DELETE FROM {_TABLE}"))
        with op.batch_alter_table(_TABLE) as batch:
            batch.drop_column("suppress_until")
            batch.add_column(sa.Column("redeemed_at", sa.DateTime(), nullable=False))
    _rewrite_kinds(lambda kinds: kinds + ["redeemed"] if "unexpected" in kinds and "redeemed" not in kinds else kinds)


def downgrade() -> None:
    _rewrite_kinds(lambda kinds: [kind for kind in kinds if kind != "redeemed"] or ["unexpected"])
    if "redeemed_at" in _columns():
        op.execute(sa.text(f"DELETE FROM {_TABLE}"))
        with op.batch_alter_table(_TABLE) as batch:
            batch.drop_column("redeemed_at")
            batch.add_column(sa.Column("suppress_until", sa.DateTime(), nullable=False))
