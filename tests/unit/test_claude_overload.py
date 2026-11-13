import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock

import pytest

from app.modules.claude.overload import is_transient_refusal, retry_delay, wait_for_retry
from app.modules.model_sources.forwarding import ModelSourceForwardingError


@pytest.mark.parametrize(
    "hint,expected",
    [(None, 0.3), ("2", 2), ("120", None), ("nan", None), ("invalid", None), ("Mon, 28 Sep 2026 12:00:02 GMT", 2)],
)
def test_delay(monkeypatch, hint, expected):
    monkeypatch.setattr("app.modules.claude.overload.random.uniform", lambda a, b: 0.3)
    error = ModelSourceForwardingError(status_code=529, payload={}, retry_after=hint)
    assert retry_delay(error, 0, now=datetime(2026, 9, 28, 12, tzinfo=UTC), available=10) == expected


@pytest.mark.parametrize("attempt,available,expected", [(0, 10, 0.3), (1, 10, 0.6), (2, 10, 1.2), (2, 1.2, None)])
def test_retry_delay_doubles_within_window(monkeypatch, attempt, available, expected):
    monkeypatch.setattr("app.modules.claude.overload.random.uniform", lambda a, b: 0.3)
    error = ModelSourceForwardingError(status_code=503, payload={})
    delay = retry_delay(error, attempt, now=datetime(2026, 9, 28, 12, tzinfo=UTC), available=available)
    if expected is None:
        assert delay is None
    else:
        assert delay == pytest.approx(expected)


@pytest.mark.parametrize(
    "status,headers,expected",
    [
        (503, {}, True),
        (500, {}, True),
        (529, {}, True),
        (408, {}, True),
        (409, {}, True),
        (503, {"X-Should-Retry": "false"}, False),
        (503, {"x-should-retry": "true"}, True),
        (429, {}, False),
        (400, {}, False),
        (None, {}, False),
    ],
)
def test_transient_refusal(status, headers, expected):
    error = ModelSourceForwardingError(
        status_code=status or 504, payload={}, upstream_status_code=status, upstream_headers=headers
    )
    assert is_transient_refusal(error) is expected


async def test_disconnected_wait():
    request = Mock(is_disconnected=AsyncMock(return_value=True))
    scheduler = Mock(sleep=AsyncMock())
    assert not await wait_for_retry(request, 1, clock=Mock(monotonic=lambda: 0), scheduler=scheduler)
    scheduler.sleep.assert_not_called()


async def test_wait_cancellation():
    request = Mock(is_disconnected=AsyncMock(return_value=False))
    scheduler = Mock(sleep=AsyncMock(side_effect=asyncio.CancelledError))
    with pytest.raises(asyncio.CancelledError):
        await wait_for_retry(request, 1, clock=Mock(monotonic=lambda: 0), scheduler=scheduler)
