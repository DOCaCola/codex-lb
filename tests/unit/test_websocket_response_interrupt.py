from __future__ import annotations

import json
from collections import deque
from typing import Any, cast
from unittest.mock import AsyncMock

import anyio
import pytest

from app.modules.proxy._service.support import _WebSocketRequestState
from app.modules.proxy._service.websocket.mixin import _route_websocket_response_interrupt


def _request_state(*, response_id: str | None, upstream_transport: str = "websocket") -> _WebSocketRequestState:
    request_state = _WebSocketRequestState(
        request_id="req-interrupt",
        model="gpt-6.1-sol",
        service_tier=None,
        reasoning_effort=None,
        api_key_reservation=None,
        started_at=0.0,
        transport="websocket",
    )
    request_state.response_id = response_id
    request_state.upstream_transport = upstream_transport
    return request_state


def _interrupt(response_id: str) -> dict[str, Any]:
    return {"type": "response.interrupt", "response_id": response_id, "mode": "discard_partial_items"}


async def _route(payload: dict[str, Any], *pending: _WebSocketRequestState, upstream: object = None) -> str | None:
    return await _route_websocket_response_interrupt(
        payload,
        upstream=cast(Any, upstream),
        pending_requests=deque(pending),
        pending_lock=anyio.Lock(),
    )


@pytest.mark.asyncio
async def test_interrupt_of_replayed_response_is_addressed_to_upstream_id() -> None:
    request_state = _request_state(response_id="resp_upstream")
    request_state.replay_downstream_response_id = "resp_client"

    forwarded = await _route(_interrupt("resp_client"), request_state)

    assert forwarded is not None
    assert json.loads(forwarded) == _interrupt("resp_upstream")


@pytest.mark.asyncio
async def test_interrupt_of_http_turn_is_handled_by_the_transport() -> None:
    upstream = AsyncMock()
    upstream.interrupt_http.return_value = True

    forwarded = await _route(
        _interrupt("resp_http"),
        _request_state(response_id="resp_http", upstream_transport="http"),
        upstream=upstream,
    )

    assert forwarded is None
    upstream.interrupt_http.assert_awaited_once_with("resp_http")


@pytest.mark.asyncio
async def test_interrupt_naming_no_in_flight_response_is_consumed() -> None:
    awaiting_created = _request_state(response_id=None)

    assert await _route(_interrupt("resp_finished"), awaiting_created) is None
    assert await _route(_interrupt("resp_finished")) is None
