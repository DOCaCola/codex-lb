"""Claude Code releases are adopted only as verified builds (CLI, SDK and runtime versions).

Builds verified at code review ship with the code; this table holds releases verified
later by the version check. A discovered or pinned version without a verified build is
reset to the reviewed baseline, and the release check runs again to verify newer ones.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261101_000000_claude_client_builds"
down_revision = "20261031_040000_quota_webhook_redeemed_kind"
branch_labels = None
depends_on = None

_TABLE = "claude_client_builds"
# REVIEWED_BUILDS and BASELINE_VERSION at this revision.
_REVIEWED = ("2.1.282", "2.1.316")
_BASELINE = "2.1.316"


def upgrade() -> None:
    if _TABLE not in sa.inspect(op.get_bind()).get_table_names():
        op.create_table(
            _TABLE,
            sa.Column("version", sa.String(), primary_key=True),
            sa.Column("sdk_version", sa.String(), nullable=False),
            sa.Column("runtime_version", sa.String(), nullable=False),
            sa.Column("package", sa.String(), nullable=False),
            sa.Column("integrity", sa.String(), nullable=False),
            sa.Column("verified_at", sa.DateTime(), nullable=False),
        )
    reviewed = sa.bindparam("reviewed", _REVIEWED, expanding=True)
    op.get_bind().execute(
        sa.text(
            "UPDATE claude_version_state SET discovered_version = :baseline, "
            "last_checked_at = NULL, etag = NULL WHERE discovered_version NOT IN :reviewed"
        ).bindparams(reviewed),
        {"baseline": _BASELINE},
    )
    op.get_bind().execute(
        sa.text(
            "UPDATE claude_version_state SET pinned_version = NULL WHERE pinned_version NOT IN :reviewed"
        ).bindparams(sa.bindparam("reviewed", _REVIEWED, expanding=True))
    )


def downgrade() -> None:
    if _TABLE in sa.inspect(op.get_bind()).get_table_names():
        op.drop_table(_TABLE)
