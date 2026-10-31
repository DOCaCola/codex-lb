"""Rename recorded Claude plan snapshots after Anthropic's 2026-10-30 plan rename.

Max 5x became Max and Max 20x became Ultra. Each row keeps the plan recorded at
dispatch; only its key changes.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261031_000000_claude_plan_rename"
down_revision = "20261029_000000_antigravity_accounts"
branch_labels = None
depends_on = None

_RENAMES = (("max_5x", "max"), ("max_20x", "ultra"))


_UPDATE = sa.text("UPDATE request_logs SET plan_type = :new WHERE plan_type = :old")


def _rename(pairs: tuple[tuple[str, str], ...]) -> None:
    for old, new in pairs:
        op.execute(_UPDATE.bindparams(old=old, new=new))


def upgrade() -> None:
    _rename(_RENAMES)


def downgrade() -> None:
    _rename(tuple((new, old) for old, new in _RENAMES))
