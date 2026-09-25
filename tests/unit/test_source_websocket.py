from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, Mock

import anyio
import pytest
from starlette.responses import StreamingResponse
from starlette.websockets import WebSocket

from app.db.models import ModelSource
from app.modules.model_sources import websocket as bridge
from app.modules.proxy import api
from app.modules.proxy.service import ProxyService

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("external_cancel", [False, True])
async def test_disconnect_closes_owned_stream_and_preserves_outer_cancellation(monkeypatch, external_cancel):
    incoming = asyncio.Queue()
    outgoing = asyncio.Queue()
    await incoming.put({"type": "websocket.connect"})
    websocket = WebSocket({"type": "websocket", "path": "/v1/responses", "headers": []}, incoming.get, outgoing.put)
    await websocket.accept()
    await outgoing.get()
    started = asyncio.Event()
    closed = asyncio.Event()

    async def body():
        try:
            started.set()
            await asyncio.Event().wait()
            yield "data: {}\n\n"
        finally:
            closed.set()

    async def route(*args, **kwargs):
        return StreamingResponse(body())

    source = Mock(spec=ModelSource)
    monkeypatch.setattr(bridge, "select_responses_model_source", AsyncMock(return_value=(source, "test")))
    monkeypatch.setattr(api, "v1_responses", route)
    service = Mock(spec=ProxyService)
    service._refresh_websocket_api_key_policy = AsyncMock(return_value=None)
    receiver = bridge.SourceWebSocketReceiver(websocket)
    turn = asyncio.create_task(
        bridge.handle_source_frame(
            websocket,
            receiver,
            {"type": "response.create", "model": "test", "input": "Hi"},
            service=service,
            api_key=None,
            send_lock=anyio.Lock(),
            native_turn_pending=False,
            native_codex=False,
        )
    )
    try:
        await asyncio.wait_for(started.wait(), 2)
        if external_cancel:
            turn.cancel()
            with pytest.raises(asyncio.CancelledError):
                await turn
        else:
            await incoming.put({"type": "websocket.disconnect", "code": 1000})
            assert await asyncio.wait_for(turn, 2) is True
            assert receiver.pending is not None
            assert receiver.pending["type"] == "websocket.disconnect"
        assert closed.is_set()
    finally:
        if not turn.done():
            turn.cancel()
        await asyncio.gather(turn, return_exceptions=True)
