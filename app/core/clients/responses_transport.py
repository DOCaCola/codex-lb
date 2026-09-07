"""Per-create transport selection behind the Responses connection contract."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncGenerator, Awaitable, Callable, Coroutine
from contextlib import aclosing

from app.core.clients.proxy import ProxyResponseError
from app.core.clients.proxy_websocket import UpstreamWebSocket, UpstreamWebSocketMessage
from app.core.errors import synthetic_stream_failure_event
from app.core.utils.request_id import get_request_id
from app.core.utils.sse import parse_sse_data_json

logger = logging.getLogger(__name__)


class ResponsesTransport:
    """Merge HTTP SSE turns and WS events without changing the downstream socket.

    The owner already enforces turn admission and associates response IDs with
    reservations. A one-event queue propagates downstream backpressure to HTTP;
    every producer is owned and joined by close(). No sent turn is retried here.
    """

    def __init__(
        self,
        websocket: UpstreamWebSocket | None,
        *,
        connect: Callable[[], Awaitable[UpstreamWebSocket]],
        stream_http: Callable[[str], AsyncGenerator[str, None]],
        max_frame_bytes: int,
    ) -> None:
        self._websocket = websocket
        self._connect = connect
        self._stream_http = stream_http
        self._max_frame_bytes = max_frame_bytes
        self._events: asyncio.Queue[UpstreamWebSocketMessage] = asyncio.Queue(maxsize=1)
        self._tasks: set[asyncio.Task[None]] = set()
        self._reader: asyncio.Task[None] | None = None
        self._closed = False
        self._websocket_ended = False
        self._send_lock = asyncio.Lock()
        self._http_idle = asyncio.Event()
        self._http_idle.set()

    def _spawn(self, coroutine: Coroutine[None, None, None]) -> asyncio.Task[None]:
        task = asyncio.create_task(coroutine, name="responses-transport-relay")
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return task

    async def _read_websocket(self, websocket: UpstreamWebSocket) -> None:
        try:
            while True:
                message = await websocket.receive()
                if message.kind in {"close", "closed", "error"}:
                    self._websocket_ended = True
                    # A WS close cannot cancel an independently running HTTP
                    # turn. Let its terminal event settle before retiring the
                    # shared connection in the service relay.
                    await self._http_idle.wait()
                await self._events.put(message)
                if message.kind in {"close", "closed", "error"}:
                    return
        except Exception:
            self._websocket_ended = True
            logger.exception("Responses websocket reader failed")
            await self._http_idle.wait()
            await self._events.put(UpstreamWebSocketMessage(kind="error", error="Upstream websocket read failed"))

    async def _read_http(self, text: str) -> None:
        response_id = get_request_id()
        try:
            async with aclosing(self._stream_http(text)) as events:
                async for block in events:
                    payload = parse_sse_data_json(block)
                    if payload is not None:
                        response = payload.get("response")
                        if isinstance(response, dict):
                            event_response_id = response.get("id")
                            if isinstance(event_response_id, str):
                                response_id = event_response_id
                        await self._events.put(
                            UpstreamWebSocketMessage(
                                kind="text", text=json.dumps(payload, separators=(",", ":")), transport="http"
                            )
                        )
        except ProxyResponseError as exc:
            error = exc.payload["error"]
            await self._events.put(
                UpstreamWebSocketMessage(
                    kind="text",
                    transport="http",
                    text=json.dumps(
                        synthetic_stream_failure_event(
                            error.get("code") or "upstream_error",
                            error.get("message") or "Upstream HTTP request failed",
                            error_type=error.get("type") or "server_error",
                            response_id=response_id,
                            error_param=error.get("param"),
                        )
                    ),
                )
            )
        except Exception:
            logger.exception("Responses HTTP relay failed")
            await self._events.put(
                UpstreamWebSocketMessage(
                    kind="text",
                    transport="http",
                    text=json.dumps(
                        synthetic_stream_failure_event(
                            "upstream_reset",
                            "Upstream HTTP stream failed",
                            response_id=response_id,
                        )
                    ),
                )
            )

    async def send_text(self, text: str) -> None:
        async with self._send_lock:
            await self._check_send_open()
            if len(text.encode("utf-8")) > self._max_frame_bytes:
                # Serialize HTTP turns on this connection. Unlike a native WS
                # send, each HTTP turn allocates a response and producer task.
                await self._http_idle.wait()
                await self._check_send_open()
                logger.info(
                    "responses_transport_selected transport=http reason=frame_size bytes=%s", len(text.encode("utf-8"))
                )
                self._http_idle.clear()
                task = self._spawn(self._read_http(text))
                task.add_done_callback(lambda _: self._http_idle.set())
                return
            websocket = await self._connected_websocket()
            await websocket.send_text(text)
            if self._reader is None:
                self._reader = self._spawn(self._read_websocket(websocket))

    async def _check_send_open(self) -> None:
        if self._closed:
            raise RuntimeError("Responses connection is closed")
        if self._websocket_ended:
            # Do not dispatch another turn behind a pending close event. Wait
            # for the independent HTTP owner before the service retires this
            # connection and retries the still-unsent request.
            await self._http_idle.wait()
            raise RuntimeError("Upstream websocket has closed")

    async def _connected_websocket(self) -> UpstreamWebSocket:
        if self._websocket is None:
            websocket = await self._connect()
            if self._closed:
                await websocket.close()
                raise RuntimeError("Responses connection closed during websocket connect")
            self._websocket = websocket
        return self._websocket

    async def send_bytes(self, data: bytes) -> None:
        async with self._send_lock:
            await self._check_send_open()
            websocket = await self._connected_websocket()
            await websocket.send_bytes(data)
            if self._reader is None:
                self._reader = self._spawn(self._read_websocket(websocket))

    async def receive(self) -> UpstreamWebSocketMessage:
        if not self._closed and self._websocket is not None and self._reader is None:
            self._reader = self._spawn(self._read_websocket(self._websocket))
        return await self._events.get()

    def response_header(self, name: str) -> str | None:
        return self._websocket.response_header(name) if self._websocket is not None else None

    def archive_received(self, message: UpstreamWebSocketMessage) -> None:
        # HTTP is archived by stream_responses at its own wire boundary.
        if message.transport == "websocket":
            archive = getattr(self._websocket, "archive_received", None)
            if callable(archive):
                archive(message)

    @property
    def upstream_proxy_route_mode(self) -> str | None:
        return getattr(self._websocket, "upstream_proxy_route_mode", None)

    @property
    def upstream_proxy_pool_id(self) -> str | None:
        return getattr(self._websocket, "upstream_proxy_pool_id", None)

    @property
    def upstream_proxy_endpoint_id(self) -> str | None:
        return getattr(self._websocket, "upstream_proxy_endpoint_id", None)

    @property
    def upstream_proxy_fallback_used(self) -> bool | None:
        return getattr(self._websocket, "upstream_proxy_fallback_used", None)

    async def close(self, code: int = 1000, reason: str = "") -> None:
        self._closed = True
        tasks = tuple(self._tasks)
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._http_idle.set()
        if self._websocket is not None:
            await self._websocket.close(code=code, reason=reason)
        # Wake an idle receive without allowing a full event queue to block close.
        while not self._events.empty():
            self._events.get_nowait()
        self._events.put_nowait(UpstreamWebSocketMessage(kind="closed", close_code=code, close_reason=reason))
