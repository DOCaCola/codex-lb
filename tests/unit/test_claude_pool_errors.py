import math
from datetime import UTC, datetime, timedelta

import pytest

from app.modules.claude import routing
from app.modules.claude.credentials import ClaudeError
from app.modules.claude.routing import ClaudePoolUnavailable

pytestmark = pytest.mark.unit
NOW = datetime(2026, 10, 1, 11, 0, tzinfo=UTC)


@pytest.mark.parametrize("seconds,expected", [(300.1, 301), (0.1, 1), (-1, 1)])
def test_reset_details_share_ceil_rounded_retry_timing(monkeypatch, seconds, expected):
    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return NOW

    monkeypatch.setattr(routing, "datetime", FixedDateTime)
    deadline = NOW + timedelta(seconds=seconds)
    error = ClaudePoolUnavailable(
        "previous_response_owner_unavailable", "quota blocked", status_code=429, retry_at=deadline, resets_at=deadline
    )
    assert error.response_headers == {"Retry-After": str(expected)}
    assert error.error_detail == {
        "type": "rate_limit_error",
        "code": "previous_response_owner_unavailable",
        "message": "quota blocked",
        "resets_at": math.ceil(deadline.timestamp()),
        "resets_in_seconds": expected,
    }
    # Codex parses resets_at as integer seconds and only usage_limit_reached
    # as a usage limit; the Anthropic dialect keeps rate_limit_error.
    assert error.responses_error_detail == {**error.error_detail, "type": "usage_limit_reached"}
    assert isinstance(error.responses_error_detail["resets_at"], int)


def test_unknown_reset_is_not_invented():
    error = ClaudePoolUnavailable("previous_response_owner_unavailable", "quota blocked", status_code=429)
    assert error.response_headers == {}
    assert error.error_detail == {
        "type": "rate_limit_error",
        "code": "previous_response_owner_unavailable",
        "message": "quota blocked",
    }
    assert error.responses_error_detail["type"] == "usage_limit_reached"


def test_non_quota_pool_error_keeps_its_type_in_both_dialects():
    error = ClaudePoolUnavailable("claude_pool_unavailable", "unavailable")
    assert error.error_detail["type"] == error.responses_error_detail["type"] == "server_error"
    assert error.messages_response_headers == error.response_headers == {}


@pytest.mark.parametrize(
    "claim,window",
    [("five_hour", "5h"), ("seven_day", "7d"), ("seven_day_overage_included", "7d_oi"), ("seven_day_opus", None)],
)
def test_local_quota_refusal_carries_unified_headers(monkeypatch, claim, window):
    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return NOW

    monkeypatch.setattr(routing, "datetime", FixedDateTime)
    reset = NOW + timedelta(seconds=7200.5)
    error = ClaudePoolUnavailable(
        "claude_pool_rate_limited", "quota", status_code=429, retry_at=reset, resets_at=reset, quota_claim=claim
    )
    epoch = str(math.ceil(reset.timestamp()))
    expected = {
        "Retry-After": "7201",
        "anthropic-ratelimit-unified-status": "rejected",
        "anthropic-ratelimit-unified-representative-claim": claim,
        "anthropic-ratelimit-unified-reset": epoch,
    }
    if window is not None:
        expected |= {
            f"anthropic-ratelimit-unified-{window}-status": "rejected",
            f"anthropic-ratelimit-unified-{window}-reset": epoch,
            f"anthropic-ratelimit-unified-{window}-utilization": "1",
        }
    assert error.messages_response_headers == expected
    # The Responses dialect keeps its own contract.
    assert error.response_headers == {"Retry-After": "7201"}


def test_local_quota_refusal_without_known_reset_claims_nothing():
    error = ClaudePoolUnavailable("claude_pool_rate_limited", "quota", status_code=429)
    assert error.messages_response_headers == {"anthropic-ratelimit-unified-status": "rejected"}


def test_ordinary_claude_error_has_no_quota_headers():
    assert ClaudeError("invalid request").messages_response_headers == {}


def test_ordinary_claude_error_retains_its_public_shape():
    error = ClaudeError("invalid request")
    assert error.error_detail == {
        "type": "invalid_request_error",
        "code": "claude_invalid_request",
        "message": "invalid request",
    }
    assert error.responses_error_detail == error.error_detail
    assert error.response_headers == {}
