from datetime import UTC, datetime, timedelta

import pytest

from app.modules.claude.failover import SendBudget, classify_refusal
from app.modules.model_sources.forwarding import ModelSourceForwardingError

pytestmark = pytest.mark.unit
NOW = datetime(2026, 9, 28, tzinfo=UTC)


def refusal(message="limited", retry=None, headers=None, status=429):
    return classify_refusal(
        ModelSourceForwardingError(
            status_code=status,
            upstream_status_code=status,
            payload={"error": {"message": message}},
            retry_after=retry,
            upstream_headers=headers,
        ),
        now=NOW,
    )


@pytest.mark.parametrize("message", ["Usage credits are required for fast mode.", "Fast request rejected"])
def test_entitlement_does_not_cool(message):
    assert refusal(message) is None


@pytest.mark.parametrize("retry", ["120", "Mon, 28 Sep 2026 00:02:00 GMT"])
def test_retry_after_priority(retry):
    result = refusal(retry=retry, headers={"anthropic-ratelimit-unified-status": "rejected"})
    assert result.scope == "account"
    assert result.until == NOW + timedelta(seconds=120)
    assert result.reason == "retry_after"


def test_rejected_reset_only():
    result = refusal(
        headers={
            "anthropic-ratelimit-unified-5h-status": "rejected",
            "anthropic-ratelimit-unified-5h-reset": str((NOW + timedelta(hours=2)).timestamp()),
            "anthropic-ratelimit-unified-7d-status": "allowed",
            "anthropic-ratelimit-unified-7d-reset": str((NOW + timedelta(days=6)).timestamp()),
        }
    )
    assert result.until == NOW + timedelta(hours=2)
    assert result.reason == "reset"


@pytest.mark.parametrize("retry", [None, "invalid", "NaN", "inf"])
def test_model_limit_defaults(retry):
    result = refusal(retry=retry)
    assert result.scope == "model"
    assert result.until == NOW + timedelta(seconds=60)


def test_non_429_not_retried():
    assert refusal(status=500) is None


def test_budget_counts_physical_sends():
    budget = SendBudget()
    for _ in range(4):
        budget.consume()
    with pytest.raises(RuntimeError):
        budget.consume()
