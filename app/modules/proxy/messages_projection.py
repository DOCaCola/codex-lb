"""Serve a Responses dispatch result as an Anthropic Messages response."""

from __future__ import annotations

import codecs
import json
from collections.abc import AsyncIterable, AsyncIterator
from typing import Final

from fastapi.responses import JSONResponse, Response, StreamingResponse

from app.core.clock import Clock
from app.core.messages.errors import anthropic_error
from app.core.messages.stream import MessagesStreamProjector, aggregate_message
from app.core.types import JsonValue
from app.core.utils.sse import ParsedSseBlock, format_sse_event, inject_sse_keepalives, parse_sse_data_json

# Before the first output the response is withheld so an upstream failure can still become an
# HTTP error (Claude Code compacts only on a 400 "prompt is too long"). Long silent reasoning
# must not hold the response headers indefinitely (agent-lb split_startup_error).
_STARTUP_GRACE_SECONDS: Final = 10.0
_TICK_SECONDS: Final = 1.0
_TICK: Final = "\x00messages-tick"
_KEEPALIVE: Final = "keepalive"
_PING: Final = format_sse_event({"type": "ping"})
_DROPPED_HEADERS: Final = frozenset({"content-length", "content-type"})

type _Event = dict[str, JsonValue] | str


async def messages_response(
    response: Response, projector: MessagesStreamProjector, *, stream: bool, clock: Clock
) -> Response:
    headers = {key: value for key, value in response.headers.items() if key.lower() not in _DROPPED_HEADERS}
    if not isinstance(response, StreamingResponse):
        return _error_response(response, headers)
    events = _responses_events(
        inject_sse_keepalives(_text_chunks(response.body_iterator), _TICK_SECONDS, keepalive_frame=_TICK)
    ).__aiter__()
    if not stream:
        collected: list[dict[str, JsonValue]] = []
        async for event in events:
            if isinstance(event, dict):
                collected.extend(projector.feed(event))
        collected.extend(projector.end_of_stream())
        if projector.error is not None:
            status, body = projector.error
            return JSONResponse(body, status_code=status, headers=headers, background=response.background)
        return JSONResponse(
            aggregate_message(projector.message_start(), collected), headers=headers, background=response.background
        )

    prelude = await _startup(events, projector, clock)
    if projector.failure is not None:
        await _drain(events)
        status, body = projector.failure
        return JSONResponse(body, status_code=status, headers=headers, background=response.background)
    return StreamingResponse(
        _stream(events, projector, prelude),
        headers=headers,
        media_type="text/event-stream",
        background=response.background,
    )


async def _startup(
    events: AsyncIterator[_Event], projector: MessagesStreamProjector, clock: Clock
) -> list[dict[str, JsonValue]]:
    deadline = clock.monotonic() + _STARTUP_GRACE_SECONDS
    while clock.monotonic() < deadline:
        try:
            event = await anext(events)
        except StopAsyncIteration:
            return projector.end_of_stream()
        if isinstance(event, dict) and (output := projector.feed(event)):
            return output
        if projector.failure is not None:
            return []
    return []


async def _stream(
    events: AsyncIterator[_Event], projector: MessagesStreamProjector, prelude: list[dict[str, JsonValue]]
) -> AsyncIterator[str]:
    yield format_sse_event(projector.message_start())
    for event in prelude:
        yield format_sse_event(event)
    async for event in events:
        if isinstance(event, dict):
            for output in projector.feed(event):
                yield format_sse_event(output)
        elif event == _KEEPALIVE and not projector.terminal:
            yield _PING
    for output in projector.end_of_stream():
        yield format_sse_event(output)


async def _drain(events: AsyncIterator[_Event]) -> None:
    # Consume the dispatch stream to its end so its settlement and request logging complete.
    async for _event in events:
        pass


async def _text_chunks(body: AsyncIterable[str | bytes | memoryview]) -> AsyncIterator[str]:
    decoder = codecs.getincrementaldecoder("utf-8")()
    async for chunk in body:
        yield chunk if isinstance(chunk, str) else decoder.decode(chunk)


async def _responses_events(chunks: AsyncIterator[str]) -> AsyncIterator[_Event]:
    buffer = ""
    async for chunk in chunks:
        if chunk == _TICK:
            yield _TICK
            continue
        if isinstance(chunk, ParsedSseBlock) and not buffer and chunk.payload is not None:
            yield _event_or_keepalive(chunk.payload)
            continue
        buffer += chunk.replace("\r\n", "\n")
        while "\n\n" in buffer:
            block, buffer = buffer.split("\n\n", 1)
            if not block.strip():
                continue
            if all(line.startswith(":") for line in block.split("\n") if line):
                yield _KEEPALIVE
                continue
            payload = parse_sse_data_json(block + "\n\n")
            if payload is not None:
                yield _event_or_keepalive(payload)


def _event_or_keepalive(payload: dict[str, JsonValue]) -> _Event:
    return _KEEPALIVE if payload.get("type") == "codex.keepalive" else payload


def _error_response(response: Response, headers: dict[str, str]) -> JSONResponse:
    error: JsonValue = None
    try:
        body = json.loads(bytes(response.body))
    except ValueError:
        body = None
    if isinstance(body, dict):
        error = body.get("error")
    status, envelope = anthropic_error(response.status_code, error if isinstance(error, dict) else None)
    return JSONResponse(envelope, status_code=status, headers=headers, background=response.background)
