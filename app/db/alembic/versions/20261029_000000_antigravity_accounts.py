"""Antigravity accounts, OAuth flows, verified client builds, quota history and cooldowns."""

from datetime import datetime

import sqlalchemy as sa
from alembic import op

revision = "20261029_000000_antigravity_accounts"
down_revision = "20261028_000000_claude_resource_identity"
branch_labels = None
depends_on = None

# CLI 1.4.10 archives, SHA-512-verified against the update manifest and stamp-extracted on
# 2026-10-29: the starting identity of a fresh install.
_ARCHIVE_BASE = "https://storage.googleapis.com/antigravity-public/antigravity-cli/1.4.10-5501573669978112"
_SEEDED_BUILDS = (
    (
        "darwin_arm64",
        "21e18868b63a35555919586f13dedf8d590151b4f818e5eec5cc85a17fb22530"
        "f7dc705fdd627766373317123bafc0b6e0ec25a33d31f144c6014120ae60c6a8",
        f"{_ARCHIVE_BASE}/darwin-arm/cli_mac_arm64.tar.gz",
    ),
    (
        "linux_arm64",
        "0182c23882b174c6f2968ad88de43262692ec363a938031319131551dab41cc6"
        "aca573d28d264095db357e49881a211114afe9f974386ed37208760f401ba98c",
        f"{_ARCHIVE_BASE}/linux-arm/cli_linux_arm64.tar.gz",
    ),
)


def upgrade() -> None:
    op.add_column("dashboard_settings", sa.Column("antigravity_single_account_id", sa.String(), nullable=True))
    op.create_table(
        "antigravity_accounts",
        sa.Column("source_id", sa.String(), sa.ForeignKey("model_sources.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("routing_policy", sa.String(), nullable=False, server_default="normal"),
        sa.Column("credentials_encrypted", sa.LargeBinary(), nullable=False),
        sa.Column("google_subject", sa.String(), nullable=False, unique=True),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=True),
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("credential_status", sa.String(), nullable=False, server_default="ready"),
        sa.Column("hold", sa.String(), nullable=True),
        sa.Column("hold_reason", sa.Text(), nullable=True),
        sa.Column("hold_at", sa.DateTime(), nullable=True),
        sa.Column("generation", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("retry_at", sa.DateTime(), nullable=True),
        sa.Column("state_json", sa.Text(), nullable=False),
        sa.Column("last_selected_at", sa.DateTime(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_table(
        "antigravity_oauth_flows",
        sa.Column("state_hash", sa.String(), primary_key=True),
        sa.Column("verifier_encrypted", sa.LargeBinary(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column(
            "source_id",
            sa.String(),
            sa.ForeignKey("antigravity_accounts.source_id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
    )
    builds = op.create_table(
        "antigravity_client_builds",
        sa.Column("sha512", sa.String(), primary_key=True),
        sa.Column("platform", sa.String(), nullable=False, index=True),
        sa.Column("version", sa.String(), nullable=False),
        sa.Column("changelist", sa.String(), nullable=False),
        sa.Column("build_id", sa.String(), nullable=True),
        sa.Column("archive_url", sa.String(), nullable=True),
        sa.Column("verified_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "antigravity_version_state",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("platform", sa.String(), nullable=False),
        sa.Column("current_sha512", sa.String(), nullable=True),
        sa.Column("pinned_sha512", sa.String(), nullable=True),
        sa.Column("last_checked_at", sa.DateTime(), nullable=True),
        sa.Column("retry_at", sa.DateTime(), nullable=True),
        sa.Column("error", sa.String(), nullable=True),
    )
    op.create_table(
        "antigravity_quota_history",
        sa.Column(
            "source_id",
            sa.String(),
            sa.ForeignKey("antigravity_accounts.source_id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("observed_at", sa.DateTime(), primary_key=True),
        sa.Column("family", sa.String(), primary_key=True),
        sa.Column("window", sa.String(), primary_key=True),
        sa.Column("used_percent", sa.Float(), nullable=False),
        sa.Column("resets_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "antigravity_cooldowns",
        sa.Column(
            "source_id",
            sa.String(),
            sa.ForeignKey("antigravity_accounts.source_id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("scope", sa.String(), primary_key=True),
        sa.Column("until", sa.DateTime(), nullable=False),
        sa.Column("reason", sa.String(), nullable=False),
    )
    op.create_table(
        "antigravity_session_owners",
        sa.Column("scope_hash", sa.String(), primary_key=True),
        sa.Column(
            "source_id",
            sa.String(),
            sa.ForeignKey("antigravity_accounts.source_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(), nullable=False, index=True),
    )
    verified_at = datetime(2026, 10, 29, 4, 0, 0)
    op.bulk_insert(
        builds,
        [
            {
                "sha512": sha,
                "platform": platform,
                "version": "1.4.10",
                "changelist": "1009308193",
                "build_id": "1.4.10-5501573669978112",
                "archive_url": url,
                "verified_at": verified_at,
            }
            for platform, sha, url in _SEEDED_BUILDS
        ],
    )


def downgrade() -> None:
    for table in (
        "antigravity_session_owners",
        "antigravity_cooldowns",
        "antigravity_quota_history",
        "antigravity_version_state",
        "antigravity_client_builds",
        "antigravity_oauth_flows",
        "antigravity_accounts",
    ):
        op.drop_table(table)
    with op.batch_alter_table("dashboard_settings") as batch:
        batch.drop_column("antigravity_single_account_id")
