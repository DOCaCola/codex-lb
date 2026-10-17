from __future__ import annotations

import asyncio
from typing import Any, cast

import pytest

import app.core.resilience.bulkhead as bulkhead_module
from app.core.resilience.bulkhead import BulkheadMiddleware, BulkheadSemaphore
from app.core.resilience.websocket_reclaim import IdleWebSocketReclaimer
from app.modules.proxy._service.support import _DownstreamWebSocketActivity
from tests.simulation.virtual_time import VirtualClock

pytestmark = pytest.mark.unit

_RESPONSES_SCOPE = {"type": "websocket", "path": "/backend-api/codex/responses"}


def _activity(clock: VirtualClock, **fields: Any) -> _DownstreamWebSocketActivity:
    activity = _DownstreamWebSocketActivity(clock=clock)
    for name, value in fields.items():
        setattr(activity, name, value)
    return activity


def test_reclaimer_requests_least_recently_used_idle_socket():
    clock = VirtualClock()
    reclaimer = IdleWebSocketReclaimer()
    oldest_busy = _DownstreamWebSocketActivity(clock=clock, has_active_work=lambda: True)
    clock.advance(1)
    owed = _activity(clock, client_tool_results_owed=True)
    clock.advance(1)
    older_idle = _activity(clock)
    clock.advance(1)
    newer_idle = _activity(clock)
    for socket in (newer_idle, owed, oldest_busy, older_idle):
        reclaimer.register(socket)

    assert reclaimer.reclaim_least_recently_used() is True
    assert older_idle.reclaim_requested is True
    assert newer_idle.reclaim_requested is False
    assert owed.reclaim_requested is False
    assert oldest_busy.reclaim_requested is False

    # A socket already asked to close is never chosen twice.
    assert reclaimer.reclaim_least_recently_used() is True
    assert newer_idle.reclaim_requested is True
    assert reclaimer.reclaim_least_recently_used() is False


def test_client_activity_cancels_reclaim_and_unregistered_sockets_are_ignored():
    clock = VirtualClock()
    reclaimer = IdleWebSocketReclaimer()
    activity = _activity(clock)
    reclaimer.register(activity)

    activity.request_reclaim()
    activity.mark()
    assert activity.reclaimable() is True

    reclaimer.unregister(activity)
    assert reclaimer.reclaim_least_recently_used() is False


def _full_websocket_lane() -> tuple[BulkheadSemaphore, asyncio.Semaphore]:
    bulkhead = BulkheadSemaphore(proxy_http_limit=1, proxy_websocket_limit=1, dashboard_limit=1)
    _lane, sem = bulkhead.get_semaphore("websocket", _RESPONSES_SCOPE["path"])
    assert sem is not None
    return bulkhead, sem


async def _connect_once() -> dict[str, object]:
    return {"type": "websocket.connect"}


@pytest.mark.asyncio
async def test_full_lane_admits_handshake_on_reclaimed_slot():
    bulkhead, sem = _full_websocket_lane()
    reclaimer = IdleWebSocketReclaimer()
    idle = _activity(VirtualClock())
    reclaimer.register(idle)
    await sem.acquire()

    async def idle_socket_handler() -> None:
        # Stands in for the socket's receive loop closing on request.
        while not idle.reclaim_requested:
            await asyncio.sleep(0.001)
        reclaimer.unregister(idle)
        sem.release()

    admitted = asyncio.Event()

    async def inner_app(scope, receive, send):
        del scope, receive, send
        admitted.set()

    middleware = BulkheadMiddleware(cast(Any, inner_app), bulkhead=bulkhead, websocket_reclaimer=reclaimer)
    handler = asyncio.create_task(idle_socket_handler())
    await middleware(cast(Any, dict(_RESPONSES_SCOPE)), cast(Any, _connect_once), cast(Any, _no_send))
    await handler

    assert admitted.is_set()
    assert sem.locked() is False


@pytest.mark.asyncio
async def test_full_lane_without_idle_socket_rejects():
    bulkhead, sem = _full_websocket_lane()
    reclaimer = IdleWebSocketReclaimer()
    reclaimer.register(_activity(VirtualClock(), client_tool_results_owed=True))
    await sem.acquire()
    sent: list[dict[str, object]] = []

    async def send(message: dict[str, object]) -> None:
        sent.append(message)

    async def inner_app(scope, receive, send):
        raise AssertionError("must not be admitted")

    middleware = BulkheadMiddleware(cast(Any, inner_app), bulkhead=bulkhead, websocket_reclaimer=reclaimer)
    await middleware(cast(Any, dict(_RESPONSES_SCOPE)), cast(Any, _connect_once), cast(Any, send))

    assert sent[0]["status"] == 429


@pytest.mark.asyncio
async def test_full_lane_rejects_when_reclaimed_slot_is_not_released(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(bulkhead_module, "WEBSOCKET_RECLAIM_ADMISSION_WAIT_SECONDS", 0.01)
    bulkhead, sem = _full_websocket_lane()
    reclaimer = IdleWebSocketReclaimer()
    idle = _activity(VirtualClock())
    reclaimer.register(idle)
    await sem.acquire()
    sent: list[dict[str, object]] = []

    async def send(message: dict[str, object]) -> None:
        sent.append(message)

    async def inner_app(scope, receive, send):
        raise AssertionError("must not be admitted")

    middleware = BulkheadMiddleware(cast(Any, inner_app), bulkhead=bulkhead, websocket_reclaimer=reclaimer)
    await middleware(cast(Any, dict(_RESPONSES_SCOPE)), cast(Any, _connect_once), cast(Any, send))

    assert idle.reclaim_requested is True
    assert sent[0]["status"] == 429
    assert sem.locked() is True


async def _no_send(message: dict[str, object]) -> None:
    del message
