"""Scheduler ownership of request-log persistence spawns and rewrite retries.

``_RequestLogMixin`` detaches the request-log INSERT and the images model
rewrite as tasks; the rewrite then waits on this request's pending insert
and backs off while the row is missing. All of that runs through the owner's
scheduler and clock so a simulation owns the tasks and drives the 30 s
backstop without wall time. ``drain_persistence_tasks`` (shutdown) stays on
the loop clock by design.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable
from types import SimpleNamespace
from typing import Any, cast

import pytest

from app.modules.proxy import service as proxy_service
from tests.simulation.virtual_time import VirtualClock, VirtualScheduler

pytestmark = pytest.mark.unit


class _RecordingVirtualScheduler(VirtualScheduler):
    def __init__(self, clock: VirtualClock) -> None:
        super().__init__(clock)
        self.task_names: list[str | None] = []
        self.sleeps: list[float] = []
        self.wait_for_timeouts: list[float | None] = []

    def create_task(self, coroutine: Any, *, name: str | None = None) -> asyncio.Task[Any]:
        self.task_names.append(name)
        return super().create_task(coroutine, name=name)

    async def sleep(self, delay: float, result: Any = None) -> Any:
        self.sleeps.append(delay)
        return await super().sleep(delay, result=result)

    async def wait_for(self, awaitable: Awaitable[Any], timeout: float | None) -> Any:
        self.wait_for_timeouts.append(timeout)
        return await super().wait_for(awaitable, timeout)


class _RequestLogsRepo:
    def __init__(self) -> None:
        self.rows: list[dict[str, object]] = []
        self.insert_release: asyncio.Event | None = None

    async def add_log(self, **kwargs: object) -> None:
        if self.insert_release is not None:
            await self.insert_release.wait()
        self.rows.append(dict(kwargs))


class _RepoContext:
    def __init__(self, repos: Any) -> None:
        self._repos = repos

    async def __aenter__(self) -> Any:
        return self._repos

    async def __aexit__(self, *_exc: object) -> bool:
        return False


def _service(scheduler: _RecordingVirtualScheduler, request_logs: _RequestLogsRepo) -> proxy_service.ProxyService:
    repos = SimpleNamespace(request_logs=request_logs)
    return proxy_service.ProxyService(
        cast(Any, lambda: _RepoContext(repos)),
        clock=scheduler.clock,
        scheduler=scheduler,
    )


async def _write_log(service: proxy_service.ProxyService, request_id: str) -> None:
    await service._write_request_log(
        account_id="acc-log",
        api_key=None,
        request_id=request_id,
        model="gpt-5.5",
        latency_ms=12,
        status="success",
    )


@pytest.mark.asyncio
async def test_write_request_log_spawns_scheduler_owned_persistence_task() -> None:
    scheduler = _RecordingVirtualScheduler(VirtualClock())
    request_logs = _RequestLogsRepo()
    service = _service(scheduler, request_logs)

    await _write_log(service, "req-log")

    assert scheduler.task_names == ["proxy-request-log-req-log"]
    (task,) = scheduler.owned_tasks
    assert task in service._request_log_tasks
    assert request_logs.rows == []
    await scheduler.drain()
    assert [row["request_id"] for row in request_logs.rows] == ["req-log"]
    assert not service._request_log_tasks
    assert not scheduler.owned_tasks


@pytest.mark.asyncio
async def test_log_handoff_retains_operation_after_ingress_context_ends():
    from app.core.usage.request_operation import RequestOperation, reset_request_operation, set_request_operation

    scheduler = _RecordingVirtualScheduler(VirtualClock())
    request_logs = _RequestLogsRepo()
    service = _service(scheduler, request_logs)
    token = set_request_operation(RequestOperation.WEB_SEARCH)
    try:
        await _write_log(service, "search")
    finally:
        reset_request_operation(token)
    await scheduler.drain()
    assert request_logs.rows[0]["request_operation"] == RequestOperation.WEB_SEARCH


@pytest.mark.asyncio
async def test_reused_worker_logs_each_turn_operation_not_its_original_context():
    from app.core.usage.request_operation import RequestOperation, reset_request_operation, set_request_operation
    from app.modules.proxy._service.support import _WebSocketRequestState

    scheduler = _RecordingVirtualScheduler(VirtualClock())
    request_logs = _RequestLogsRepo()
    service = _service(scheduler, request_logs)
    states = []
    for operation in (RequestOperation.IMAGE_EDIT, RequestOperation.CHAT_COMPLETIONS):
        token = set_request_operation(operation)
        try:
            states.append(
                _WebSocketRequestState(
                    request_id=operation.value,
                    model="test-model",
                    service_tier=None,
                    reasoning_effort=None,
                    api_key_reservation=None,
                    started_at=0,
                )
            )
        finally:
            reset_request_operation(token)
    token = set_request_operation(RequestOperation.RESPONSES)
    try:
        for state in states:
            await service._write_websocket_connect_failure(
                account_id=None, api_key=None, request_state=state, error_code="upstream_error", error_message="test"
            )
    finally:
        reset_request_operation(token)
    await scheduler.drain()
    assert [row["request_operation"] for row in request_logs.rows] == [
        RequestOperation.IMAGE_EDIT,
        RequestOperation.CHAT_COMPLETIONS,
    ]


@pytest.mark.asyncio
async def test_stream_preflight_error_latency_uses_owner_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    scheduler = _RecordingVirtualScheduler(VirtualClock(monotonic_value=12.5))
    request_logs = _RequestLogsRepo()
    service = _service(scheduler, request_logs)
    # A wall clock far ahead of the virtual one: a leaked ``time.monotonic``
    # read would report an absurd latency.
    monkeypatch.setattr(time, "monotonic", lambda: 1_000_000.0)

    await service._write_stream_preflight_error(
        account_id="acc-preflight",
        api_key=None,
        request_id="req-preflight",
        model="gpt-5.5",
        start=10.0,
        error_code="upstream_unavailable",
        error_message="unavailable",
        reasoning_effort=None,
        service_tier=None,
    )
    await scheduler.drain()

    (row,) = request_logs.rows
    assert row["latency_ms"] == 2500
    assert row["status"] == "error"
