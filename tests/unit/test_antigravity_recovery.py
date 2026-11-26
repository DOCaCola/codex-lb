from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, cast

import pytest

from app.modules.antigravity import recovery
from app.modules.antigravity.classify import FailureKind, UpstreamFailure
from app.modules.antigravity.recovery import (
    MAX_SENDS,
    AntigravityUpstreamError,
    RecoveryState,
    client_error,
    plan_retry,
)
from app.modules.model_sources.forwarding import ModelSourceForwardingError


@pytest.fixture(autouse=True)
def fixed_jitter(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(recovery, "_jitter", lambda: 0.5)


def _state() -> RecoveryState:
    state = RecoveryState()
    state.bind("src-1", "token-1")
    return state


def _error(kind: FailureKind, *, retry_after: timedelta | None = None, message: str = "m") -> AntigravityUpstreamError:
    return AntigravityUpstreamError(UpstreamFailure(kind, 429, message, retry_after=retry_after), secret="token-1")


async def test_quota_moves_to_another_account() -> None:
    state = _state()
    assert await plan_retry(state, _error("quota")) == 0.0
    assert state.excluded == {"src-1"}


async def test_ban_ends_the_request() -> None:
    state = _state()
    error = _error("banned")
    assert error.status_code == 403
    assert error.upstream_headers == {"x-should-retry": "false"}
    assert error.retry_after is None
    assert await plan_retry(state, error) is None


async def test_short_rate_limit_waits_once_in_place() -> None:
    state = _state()
    assert await plan_retry(state, _error("rate_limit", retry_after=timedelta(seconds=2))) == 2.0
    assert state.retry_source_id == "src-1"
    assert not state.excluded
    state.bind("src-1", "token-1")
    assert await plan_retry(state, _error("rate_limit", retry_after=timedelta(seconds=2))) == 0.0
    assert state.excluded == {"src-1"}


def _unexplained(seconds: int | None) -> AntigravityUpstreamError:
    retry_after = timedelta(seconds=seconds) if seconds is not None else None
    return AntigravityUpstreamError(
        UpstreamFailure("unexplained_429", 429, "m", retry_after=retry_after), secret="token-1"
    )


async def test_unexplained_429_without_retry_after_is_reported() -> None:
    state = _state()
    assert await plan_retry(state, _unexplained(None)) is None
    assert not state.excluded


async def test_unexplained_429_never_walks_the_pool() -> None:
    state = _state()
    assert await plan_retry(state, _unexplained(0)) == 0.5
    assert state.retry_source_id == "src-1"
    state.bind("src-1", "token-1")
    assert await plan_retry(state, _unexplained(0)) is None
    assert not state.excluded


async def test_unexplained_429_waits_for_the_upstream_hint_and_reports_itself_final() -> None:
    error = _unexplained(7)
    assert error.retry_after is None
    assert error.upstream_headers == {"x-should-retry": "false"}
    assert await plan_retry(_state(), error) == 7.0


async def test_upstream_429s_are_bounded() -> None:
    state = _state()
    for _ in range(2):
        assert await plan_retry(state, _error("quota")) == 0.0
        state.bind("src-2", "token-2")
    assert await plan_retry(state, _error("quota")) is None


async def test_overload_retries_once_elsewhere() -> None:
    state = _state()
    assert await plan_retry(state, _error("overloaded")) == 0.5
    assert state.excluded == {"src-1"}
    state.bind("src-2", "token-2")
    assert await plan_retry(state, _error("overloaded")) is None


async def test_short_capacity_delay_is_waited_out_in_place() -> None:
    state = _state()
    assert await plan_retry(state, _error("overloaded", retry_after=timedelta(seconds=2))) == 2.0
    assert state.retry_source_id == "src-1"
    assert not state.excluded
    state.bind("src-1", "token-1")
    assert await plan_retry(state, _error("overloaded", retry_after=timedelta(seconds=2))) is None


async def test_long_capacity_delay_moves_without_waiting() -> None:
    state = _state()
    assert await plan_retry(state, _error("overloaded", retry_after=timedelta(seconds=17))) == 0.5
    assert state.excluded == {"src-1"}


async def test_auth_refreshes_once_then_excludes() -> None:
    state = _state()
    assert await plan_retry(state, _error("auth")) == 0.0
    assert (state.retry_source_id, state.rejected_token) == ("src-1", "token-1")
    state.bind("src-1", "token-1b")
    assert state.rejected_token is None
    assert await plan_retry(state, _error("auth")) == 0.0
    assert state.excluded == {"src-1"}


async def test_signature_rejection_repairs_once_unsigned() -> None:
    state = _state()
    assert await plan_retry(state, _error("signature")) == 0.0
    assert state.unsigned
    state.bind("src-1", "token-1")
    assert await plan_retry(state, _error("signature")) is None


@pytest.mark.parametrize("kind", ["invalid_request", "context_length", "upstream"])
async def test_request_defects_are_reported(kind: FailureKind) -> None:
    assert await plan_retry(_state(), _error(kind)) is None


async def test_location_is_reported() -> None:
    assert await plan_retry(_state(), _error("location")) is None


async def test_nothing_replays_after_the_stream_opened() -> None:
    state = _state()
    state.stream_opened = True
    assert await plan_retry(state, _error("overloaded")) is None


async def test_sends_are_bounded() -> None:
    state = _state()
    state.sends = MAX_SENDS
    assert await plan_retry(state, _error("quota")) is None


async def test_only_pre_dispatch_connection_failures_replay() -> None:
    def failure(pre_dispatch: bool) -> ModelSourceForwardingError:
        return ModelSourceForwardingError(status_code=502, payload={}, pre_dispatch=pre_dispatch)

    assert await plan_retry(_state(), failure(False)) is None
    state = _state()
    assert await plan_retry(state, failure(True)) == 0.5
    assert state.retry_source_id == "src-1"
    assert await plan_retry(state, failure(True)) is None


def test_client_errors_hide_google_details() -> None:
    reset = datetime(2026, 10, 29, 15, 0, 0, 500_000, tzinfo=UTC)
    status, payload = client_error(UpstreamFailure("quota", 429, "exhausted", reset_at=reset))
    error = cast(dict[str, Any], payload["error"])
    assert status == 429
    assert error["code"] == "usage_limit_reached"
    assert error["resets_at"] == int(reset.timestamp()) + 1
    status, payload = client_error(
        UpstreamFailure("verification", 403, "Verify at https://accounts.google.com/x?token=secret")
    )
    assert status == 503
    assert "accounts.google.com" not in cast(dict[str, Any], payload["error"])["message"]


def test_upstream_error_redacts_the_access_token_and_derives_retry_after() -> None:
    error = AntigravityUpstreamError(
        UpstreamFailure("rate_limit", 429, "token token-1 is limited", retry_after=timedelta(seconds=1.2)),
        secret="token-1",
    )
    assert "token-1" not in str(error.payload)
    assert error.retry_after == "2"
    assert error.upstream_status_code == 429
