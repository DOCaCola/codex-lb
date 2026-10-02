import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock

import pytest

from app.modules.claude.overload import connect_retry_delay, retry_delay, wait_for_retry
from app.modules.model_sources.forwarding import ModelSourceForwardingError


@pytest.mark.parametrize(
    "hint,expected",
    [(None, 0.3), ("2", 2), ("120", None), ("nan", None), ("invalid", None), ("Mon, 28 Sep 2026 12:00:02 GMT", 2)],
)
def test_delay(monkeypatch, hint, expected):
    monkeypatch.setattr("app.modules.claude.overload.random.uniform", lambda a, b: 0.3)
    error = ModelSourceForwardingError(status_code=529, payload={}, retry_after=hint)
    assert retry_delay(error, now=datetime(2026, 9, 28, 12, tzinfo=UTC), available=10) == expected


@pytest.mark.parametrize("attempt,available,expected", [(0, 10, 0.3), (1, 10, 0.6), (2, 10, 1.2), (2, 1.2, None)])
def test_connect_retry_delay_doubles_within_window(monkeypatch, attempt, available, expected):
    monkeypatch.setattr("app.modules.claude.overload.random.uniform", lambda a, b: 0.3)
    delay = connect_retry_delay(attempt, available=available)
    if expected is None:
        assert delay is None
    else:
        assert delay == pytest.approx(expected)


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
