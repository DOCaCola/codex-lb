from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock

import pytest

import app.core.clients.proxy as http_client
import app.core.clients.proxy_websocket as ws_client
from app.core.clients.proxy_websocket import UpstreamWebSocketMessage
from app.core.clients.responses_transport import ResponsesTransport
from app.core.config.settings import Settings
from app.core.upstream_proxy import ResolvedProxyEndpoint, ResolvedUpstreamRoute
from app.core.utils.sse import format_sse_event


class Socket:
    def __init__(self):
        self.sent = []
        self.events = asyncio.Queue()
        self.closed = False

    async def send_text(self, text):
        self.sent.append(text)

    async def send_bytes(self, data):
        self.sent.append(data)

    async def receive(self):
        return await self.events.get()

    def response_header(self, name):
        return "turn-state" if name == "x-codex-turn-state" else None

    async def close(self, code=1000, reason=""):
        self.closed = True


@pytest.mark.asyncio
@pytest.mark.parametrize("routed", [False, True])
async def test_oversized_turn_uses_same_account_http_and_next_small_turn_uses_ws(monkeypatch, routed):
    socket = Socket()
    connect = AsyncMock(return_value=socket)
    settings = Settings(upstream_response_create_max_bytes=1024)
    monkeypatch.setattr(ws_client, "get_settings", lambda: settings)
    monkeypatch.setattr(ws_client, "_connect_upstream_websocket", connect)
    calls = []
    route = (
        ResolvedUpstreamRoute("required", "pool", ResolvedProxyEndpoint("endpoint", "https", "proxy.test", 443))
        if routed
        else None
    )

    async def stream(payload, headers, access_token, account_id, **kwargs):
        calls.append((payload.to_payload(), headers, access_token, account_id, kwargs))
        yield format_sse_event({"type": "response.created", "response": {"id": "resp_http"}})
        yield format_sse_event({"type": "response.completed", "response": {"id": "resp_http", "output": []}})

    monkeypatch.setattr(http_client, "stream_responses", stream)
    image = {"type": "input_image", "image_url": "data:image/png;base64," + "A" * 2048}
    frame = {
        "type": "response.create",
        "model": "gpt-6-astra",
        "instructions": "",
        "input": [
            {"role": "user", "content": [image]},
            {"role": "user", "content": [{"type": "input_text", "text": "next"}]},
        ],
        "previous_response_id": "resp_previous",
        "store": False,
    }
    text = json.dumps(frame)
    transport = await ws_client.connect_responses_websocket(
        {"session_id": "session"},
        "account-token",
        "account-id",
        initial_request_text=text,
        allow_direct_egress=not routed,
        route=route,
    )
    try:
        connect.assert_not_awaited()
        await transport.send_text(text)
        assert json.loads((await transport.receive()).text)["type"] == "response.created"
        assert json.loads((await transport.receive()).text)["type"] == "response.completed"
        connect.assert_not_awaited()
        assert len(calls) == 1
        body, headers, token, account, kwargs = calls[0]
        assert body["input"] == frame["input"]
        assert body["previous_response_id"] == "resp_previous"
        assert body["store"] is False
        assert body["stream"] is True
        assert "type" not in body
        assert (headers, token, account) == ({"session_id": "session"}, "account-token", "account-id")
        assert kwargs["upstream_stream_transport_override"] == "http"
        assert kwargs["route"] is route
        assert kwargs["allow_direct_egress"] == (not routed)
        small = '{"type":"response.create","model":"gpt-6-astra","previous_response_id":"resp_http","input":[]}'
        await transport.send_text(small)
        connect.assert_awaited_once()
        assert socket.sent == [small]
        assert transport.response_header("x-codex-turn-state") == "turn-state"
    finally:
        await transport.close()
    assert socket.closed


@pytest.mark.asyncio
async def test_utf8_boundary_and_interleaved_events_preserve_existing_ws_turn():
    socket = Socket()
    http_bodies = []
    release_http = asyncio.Event()

    async def stream(text):
        http_bodies.append(text)
        yield format_sse_event({"type": "response.created", "response": {"id": "http"}})
        await release_http.wait()
        yield format_sse_event({"type": "response.completed", "response": {"id": "http"}})

    transport = ResponsesTransport(socket, connect=AsyncMock(), stream_http=stream, max_frame_bytes=8)
    try:
        await transport.send_text("é" * 4)
        assert socket.sent == ["é" * 4]
        await transport.send_text("é" * 4 + "x")
        assert json.loads((await transport.receive()).text)["response"]["id"] == "http"
        await socket.events.put(
            UpstreamWebSocketMessage(kind="text", text='{"type":"response.completed","response":{"id":"ws"}}')
        )
        assert json.loads((await transport.receive()).text)["response"]["id"] == "ws"
        release_http.set()
        assert json.loads((await transport.receive()).text)["type"] == "response.completed"
        assert http_bodies == ["é" * 4 + "x"]
        assert not socket.closed
    finally:
        await transport.close()


@pytest.mark.asyncio
async def test_close_cancels_and_joins_backpressured_http_stream():
    finalized = asyncio.Event()
    started = asyncio.Event()
    emitted = []

    async def stream(text):
        try:
            started.set()
            for i in range(100):
                emitted.append(i)
                yield format_sse_event({"type": "response.output_text.delta", "delta": str(i)})
        finally:
            finalized.set()

    transport = ResponsesTransport(None, connect=AsyncMock(), stream_http=stream, max_frame_bytes=1)
    await transport.send_text("large")
    await started.wait()
    assert len(emitted) <= 2
    await transport.close()
    assert finalized.is_set()
    assert (await transport.receive()).kind == "closed"


@pytest.mark.asyncio
async def test_ws_close_waits_for_http_terminal():
    socket = Socket()
    release = asyncio.Event()

    async def stream(text):
        yield format_sse_event({"type": "response.created", "response": {"id": "http"}})
        await release.wait()
        yield format_sse_event({"type": "response.completed", "response": {"id": "http"}})

    transport = ResponsesTransport(socket, connect=AsyncMock(), stream_http=stream, max_frame_bytes=1)
    try:
        await transport.send_text("large")
        await transport.receive()
        await socket.events.put(UpstreamWebSocketMessage(kind="closed", close_code=1000))
        release.set()
        assert json.loads((await transport.receive()).text)["type"] == "response.completed"
        assert (await transport.receive()).kind == "closed"
    finally:
        await transport.close()


@pytest.mark.asyncio
async def test_close_during_lazy_connect_disposes_unsent_socket():
    socket = Socket()
    connecting = asyncio.Event()
    release = asyncio.Event()

    async def connect():
        connecting.set()
        await release.wait()
        return socket

    async def stream(text):
        yield ""

    transport = ResponsesTransport(None, connect=connect, stream_http=stream, max_frame_bytes=1024)
    send = asyncio.create_task(transport.send_text("small"))
    await connecting.wait()
    await transport.close()
    release.set()
    with pytest.raises(RuntimeError, match="closed during websocket connect"):
        await send
    assert socket.closed
    assert socket.sent == []


@pytest.mark.asyncio
async def test_http_turn_admission_is_bounded_and_close_wakes_waiting_send():
    started = asyncio.Event()
    calls = []

    async def stream(text):
        calls.append(text)
        started.set()
        await asyncio.Event().wait()
        yield ""

    transport = ResponsesTransport(None, connect=AsyncMock(), stream_http=stream, max_frame_bytes=1)
    await transport.send_text("first")
    await started.wait()
    waiting = asyncio.create_task(transport.send_text("second"))
    await asyncio.sleep(0)
    assert not waiting.done()
    assert calls == ["first"]
    await transport.close()
    with pytest.raises(RuntimeError, match="closed"):
        await waiting
    assert calls == ["first"]


@pytest.mark.asyncio
async def test_new_http_turn_cannot_dispatch_behind_pending_ws_close():
    socket = Socket()
    release = asyncio.Event()
    calls = []

    async def stream(text):
        calls.append(text)
        yield format_sse_event({"type": "response.created", "response": {"id": "http"}})
        await release.wait()
        yield format_sse_event({"type": "response.completed", "response": {"id": "http"}})

    transport = ResponsesTransport(socket, connect=AsyncMock(), stream_http=stream, max_frame_bytes=1)
    try:
        await transport.send_text("first")
        await transport.receive()
        await socket.events.put(UpstreamWebSocketMessage(kind="closed", close_code=1000))
        await asyncio.sleep(0)
        waiting = asyncio.create_task(transport.send_text("second"))
        release.set()
        assert json.loads((await transport.receive()).text)["type"] == "response.completed"
        with pytest.raises(RuntimeError, match="websocket has closed"):
            await waiting
        assert calls == ["first"]
    finally:
        await transport.close()
