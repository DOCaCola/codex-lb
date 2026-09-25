"""Adapt source Responses turns to the existing HTTP dispatch pipeline in-process."""

from __future__ import annotations

import asyncio
import inspect
import json
import time
from typing import TYPE_CHECKING
from uuid import uuid4

import anyio
from pydantic import ValidationError
from starlette.requests import Request
from starlette.responses import StreamingResponse
from starlette.types import Message
from starlette.websockets import WebSocket

from app.core.exceptions import AppError
from app.core.openai.v1_requests import V1ResponsesRequest
from app.core.types import JsonValue
from app.core.utils.request_id import reset_request_id, set_request_id
from app.core.utils.shared_future import _await_result_deferring_cancellation
from app.core.utils.sse import parse_sse_data_json
from app.modules.api_keys.service import ApiKeyData
from app.modules.model_sources.selection import effective_model_for_api_key, select_responses_model_source
from app.modules.proxy.source_dispatch import SourceStreamingResponse

if TYPE_CHECKING:
    from app.modules.proxy.service import ProxyService


class SourceWebSocketReceiver:
    """A single lookahead slot preserves the first frame of the next turn."""

    def __init__(self, websocket: WebSocket) -> None:
        self.websocket = websocket
        self.pending: Message | None = None

    async def receive(self) -> Message:
        if self.pending is not None:
            message, self.pending = self.pending, None
            return message
        return await self.websocket.receive()

    async def next_turn_or_disconnect(self) -> Message:
        while True:
            message = await self.websocket.receive()
            if message["type"] == "websocket.receive" and message.get("text"):
                try:
                    event = json.loads(message["text"])
                except ValueError:
                    return message
                if isinstance(event, dict) and event.get("type") == "response.processed":
                    continue
            return message


async def handle_source_frame(
    websocket: WebSocket,
    receiver: SourceWebSocketReceiver,
    payload: dict[str, JsonValue],
    *,
    service: ProxyService,
    api_key: ApiKeyData | None,
    send_lock: anyio.Lock,
    native_turn_pending: bool,
    native_codex: bool,
) -> bool:
    # Import at the boundary: api.py owns the shared route policy and dispatch;
    # no second reservation/settlement implementation lives in this adapter.
    from app.dependencies import ProxyContext
    from app.modules.proxy import api

    key = await service._refresh_websocket_api_key_policy(api_key)
    requested = payload.get("model")
    if not isinstance(requested, str):
        return False
    model = effective_model_for_api_key(key, requested) or requested
    selected = await select_responses_model_source(
        model, key, raw_model=model, require_streaming=True, advance_rotation=False
    )
    disabled = (
        None
        if selected
        else await select_responses_model_source(
            model, key, raw_model=model, require_streaming=True, only_disabled=True
        )
    )
    if selected is None and disabled is None:
        return False

    async def send(event: dict[str, JsonValue]) -> None:
        async with send_lock:
            await websocket.send_text(json.dumps(event, separators=(",", ":")))

    if native_turn_pending:
        await send(
            {
                "type": "error",
                "status": 409,
                "error": {
                    "type": "invalid_request_error",
                    "code": "response_in_progress",
                    "message": "Wait for the active response before switching providers.",
                },
            }
        )
        return True

    disconnected = asyncio.Event()

    async def receive_http() -> Message:
        await disconnected.wait()
        return {"type": "http.disconnect"}

    scope = {
        **websocket.scope,
        "type": "http",
        "method": "POST",
        "state": dict(websocket.scope.get("state", {})),
        "source_websocket": True,
        "path": "/backend-api/codex/responses" if native_codex else "/v1/responses",
        # Replay identity must use client headers, not the connection-local
        # turn state synthesized for a native upstream handshake.
        "headers": websocket.scope["headers"],
    }
    request = Request(scope, receive=receive_http)
    body = {name: value for name, value in payload.items() if name != "type"}
    body["stream"] = True

    async def dispatch() -> None:
        request_id_token = set_request_id(f"ws_src_{uuid4().hex}")
        try:
            api.validate_model_access(key, model)
            if payload.get("generate") is False and selected is not None:
                response: dict[str, JsonValue] = {
                    "id": "",
                    "object": "response",
                    "created_at": int(time.time()),
                    "model": model,
                    "status": "completed",
                    "output": [],
                }
                await send(
                    {
                        "type": "response.created",
                        "sequence_number": 0,
                        "response": {**response, "status": "in_progress"},
                    }
                )
                await send({"type": "response.completed", "sequence_number": 1, "response": response})
                return
            if native_codex:
                result = await api.responses(request, body, context=ProxyContext(service=service), api_key=key)
            else:
                result = await api.v1_responses(
                    request, V1ResponsesRequest.model_validate(body), context=ProxyContext(service=service), api_key=key
                )
            if isinstance(result, StreamingResponse):
                try:
                    async for frame in api._iter_source_sse_event_blocks(result.body_iterator):
                        event = parse_sse_data_json(frame)
                        if event is not None:
                            await send(event)
                finally:
                    if isinstance(result, SourceStreamingResponse):
                        await result.owner.finalize_transport()
                    elif inspect.isasyncgen(result.body_iterator):
                        await result.body_iterator.aclose()
            elif result.status_code >= 400:
                error = json.loads(bytes(result.body))
                await send({"type": "error", "status": result.status_code, **error})
            else:
                await send({"type": "response.completed", "response": json.loads(bytes(result.body))})
        except ValidationError:
            await send(
                {
                    "type": "error",
                    "status": 400,
                    "error": {
                        "type": "invalid_request_error",
                        "code": "invalid_request",
                        "message": "Invalid Responses request",
                    },
                }
            )
        except AppError as exc:
            await send(
                {
                    "type": "error",
                    "status": exc.status_code,
                    "error": {"type": "invalid_request_error", "code": exc.code, "message": exc.message},
                }
            )
        finally:
            reset_request_id(request_id_token)

    turn = asyncio.create_task(dispatch())
    incoming = asyncio.create_task(receiver.next_turn_or_disconnect())
    try:
        await asyncio.wait((turn, incoming), return_when=asyncio.FIRST_COMPLETED)
        if incoming.done():
            receiver.pending = incoming.result()
            disconnected.set()
            if not turn.done():
                turn.cancel()
        else:
            turn.result()
    finally:
        disconnected.set()
        for task in (turn, incoming):
            if not task.done():
                task.cancel()
        _, cancellation = await _await_result_deferring_cancellation(
            asyncio.gather(turn, incoming, return_exceptions=True)
        )
        # A frame can arrive between the wait and cancellation; keep it too.
        if receiver.pending is None and not incoming.cancelled() and incoming.exception() is None:
            receiver.pending = incoming.result()
        if cancellation is not None:
            raise cancellation
    return True
