from app.core.balancer import AccountState, select_account
from app.core.routing_diagnostics import explain_unavailable
from app.db.models import AccountStatus


def test_public_explanation_has_only_category_counts_and_known_recovery():
    assert explain_unavailable("Unavailable", ["paused", "paused", "cooldown"], retry_at=1000) == (
        "Unavailable. Routing exclusions (cooldown: 1, paused: 2; known recovery: 1970-01-01T00:16:40+00:00)."
    )
    assert explain_unavailable("Unavailable", []) == "Unavailable"


def test_mixed_exclusions_do_not_claim_all_accounts_are_paused():
    result = select_account(
        [
            AccountState("private-paused", AccountStatus.PAUSED),
            AccountState("private-cooling", AccountStatus.ACTIVE, cooldown_until=1500),
        ],
        now=1000,
    )
    assert result.account is None
    assert "cooldown: 1, paused: 1" in result.error_message
    assert "private" not in result.error_message
    assert result.resets_at == 1500


def test_unknown_quota_snapshots_do_not_create_exclusions():
    result = select_account([AccountState("ready", AccountStatus.ACTIVE, used_percent=100)], now=1000)
    assert result.account is not None
