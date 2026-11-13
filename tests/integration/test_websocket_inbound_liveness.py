"""Downstream websocket keepalive must not cut off a client that is still uploading.

The Codex Responses websocket pump writes and reads in one loop, so it cannot
answer a ping while a large ``response.create`` is still being written. Stock
uvicorn fails such a connection with 1011 after ``ping_interval + ping_timeout``
regardless of the bytes arriving; ``InboundLivenessWebSocketProtocol`` counts
inbound data as liveness and still closes peers that send nothing.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import pytest
import uvicorn
from uvicorn.protocols.websockets.websockets_sansio_impl import WebSocketsSansIOProtocol
from websockets.client import ClientProtocol
from websockets.frames import Close, Frame, Opcode
from websockets.uri import parse_uri

from app.cli import _load_websocket_protocol_class

pytestmark = pytest.mark.integration

_PING_INTERVAL = 0.2
_PING_TIMEOUT = 0.3
_UPLOAD_BYTES = 64 * 1024
_UPLOAD_SECONDS = 1.5


async def _echo_length_app(scope: dict[str, Any], receive: Any, send: Any) -> None:
    assert scope["type"] == "websocket"
    await receive()
    await send({"type": "websocket.accept"})
    message = await receive()
    if message["type"] != "websocket.receive":
        return
    await send({"type": "websocket.send", "text": str(len(message["text"]))})
    await receive()


@asynccontextmanager
async def _serve(ws_protocol: type[asyncio.Protocol]) -> AsyncIterator[int]:
    config = uvicorn.Config(
        app=_echo_length_app,
        host="127.0.0.1",
        port=0,
        lifespan="off",
        ws=ws_protocol,
        ws_ping_interval=_PING_INTERVAL,
        ws_ping_timeout=_PING_TIMEOUT,
        log_level="warning",
    )
    server = uvicorn.Server(config)
    serve_task = asyncio.create_task(server.serve())
    try:
        async with asyncio.timeout(10.0):
            while not server.started:
                await asyncio.sleep(0.01)
        yield server.servers[0].sockets[0].getsockname()[1]
    finally:
        server.should_exit = True
        await serve_task


@asynccontextmanager
async def _connect(
    port: int,
) -> AsyncIterator[tuple[ClientProtocol, asyncio.StreamReader, asyncio.StreamWriter]]:
    client = ClientProtocol(parse_uri(f"ws://127.0.0.1:{port}/"))
    reader, writer = await asyncio.open_connection("127.0.0.1", port)
    client.send_request(client.connect())
    writer.write(b"".join(client.data_to_send()))
    await writer.drain()
    async with asyncio.timeout(5.0):
        client.receive_data(await reader.readuntil(b"\r\n\r\n"))
    client.events_received()
    assert client.handshake_exc is None
    try:
        yield client, reader, writer
    finally:
        writer.close()


async def _upload_slowly(client: ClientProtocol, writer: asyncio.StreamWriter) -> None:
    """Trickle one large text message without reading or answering pings."""

    client.send_text(b"x" * _UPLOAD_BYTES)
    data = b"".join(client.data_to_send())
    chunk_count = 16
    chunk_size = -(-len(data) // chunk_count)
    for offset in range(0, len(data), chunk_size):
        writer.write(data[offset : offset + chunk_size])
        await writer.drain()
        await asyncio.sleep(_UPLOAD_SECONDS / chunk_count)


async def _next_text_or_close(client: ClientProtocol, reader: asyncio.StreamReader) -> str | Close | None:
    async with asyncio.timeout(5.0):
        while True:
            data = await reader.read(65536)
            if not data:
                return None
            client.receive_data(data)
            for event in client.events_received():
                assert isinstance(event, Frame)
                if event.opcode == Opcode.TEXT:
                    return bytes(event.data).decode()
                if event.opcode == Opcode.CLOSE:
                    return Close.parse(event.data)


async def test_slow_upload_is_delivered_without_answering_pings() -> None:
    async with _serve(_load_websocket_protocol_class()) as port, _connect(port) as (client, reader, writer):
        await _upload_slowly(client, writer)
        assert await _next_text_or_close(client, reader) == str(_UPLOAD_BYTES)


async def test_stock_protocol_cuts_off_the_same_slow_upload() -> None:
    """Canary: if this starts passing upload delivery, the subclass can be retired."""

    async with _serve(WebSocketsSansIOProtocol) as port, _connect(port) as (client, reader, writer):
        outcome_task = asyncio.create_task(_next_text_or_close(client, reader))
        try:
            await _upload_slowly(client, writer)
        except ConnectionError:
            pass
        outcome = await outcome_task
        assert isinstance(outcome, Close), outcome
        assert outcome.code == 1011


async def test_silent_client_is_still_closed_by_keepalive() -> None:
    async with _serve(_load_websocket_protocol_class()) as port, _connect(port) as (client, reader, _writer):
        outcome = await _next_text_or_close(client, reader)
        assert isinstance(outcome, Close), outcome
        assert outcome.code == 1011
