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
        "previous_response_owner_unavailable", "quota blocked", status_code=429, retry_at=deadline
    )
    assert error.response_headers == {"Retry-After": str(expected)}
    assert error.error_detail == {
        "type": "rate_limit_error",
        "code": "previous_response_owner_unavailable",
        "message": "quota blocked",
        "resets_at": deadline.timestamp(),
        "resets_in_seconds": expected,
    }


def test_unknown_reset_is_not_invented():
    error = ClaudePoolUnavailable("previous_response_owner_unavailable", "quota blocked", status_code=429)
    assert error.response_headers == {}
    assert error.error_detail == {
        "type": "rate_limit_error",
        "code": "previous_response_owner_unavailable",
        "message": "quota blocked",
    }


def test_ordinary_claude_error_retains_its_public_shape():
    error = ClaudeError("invalid request")
    assert error.error_detail == {
        "type": "invalid_request_error",
        "code": "claude_invalid_request",
        "message": "invalid request",
    }
    assert error.response_headers == {}
