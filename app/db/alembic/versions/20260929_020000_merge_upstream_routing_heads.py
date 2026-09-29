"""Converge published upstream and fork migration histories."""

revision = "20260929_020000_merge_upstream_routing_heads"
down_revision = (
    "20260929_010000_claude_routing",
    "20260918_000000_merge_scim_and_overflow_heads",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
