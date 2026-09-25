"""Bounded Claude SSE transport, using the shared source connection owner."""

from __future__ import annotations

import contextlib
from collections.abc import AsyncGenerator, AsyncIterator, Mapping
from typing import cast

import aiohttp
from pydantic import ValidationError

from app.core.clients.http import lease_model_source_session
from app.core.clients.proxy import _iter_sse_events
from app.core.clients.stream_errors import StreamEventTooLargeError, StreamIdleTimeoutError
from app.core.clock import REAL_CLOCK, REAL_SCHEDULER, Clock, Scheduler
from app.core.types import JsonValue
from app.core.utils.sse import format_sse_event, parse_sse_data_json
from app.modules.claude.credentials import ClaudeError
from app.modules.claude.dispatch import PreparedClaudeRequest
from app.modules.claude.native import NativeObserver, usage_totals
from app.modules.claude.responses import ResponsesProjection, Usage
from app.modules.model_sources.forwarding import (
    SOURCE_FIRST_FRAME_DEADLINE_SECONDS,
    ModelSourceForwardingError,
    SourceResponsesCompletion,
    SourceResponsesStream,
    SourceStreamTransport,
    SourceStreamUsageParser,
    SourceUsage,
    SourceUsageHolder,
    _open_source_stream,
    _redact_json_value,
    _response_json,
    _source_client_timeout,
    source_stream_idle_seconds,
)


def _failure(code: str, message: str) -> ModelSourceForwardingError:
    return ModelSourceForwardingError(
        status_code=502,
        payload={
            "error": {
                "type": "upstream_error",
                "code": code,
                "message": message,
            }
        },
    )


async def open_responses(
    prepared: PreparedClaudeRequest,
    projection: ResponsesProjection | None,
    *,
    scheduler: Scheduler = REAL_SCHEDULER,
    clock: Clock = REAL_CLOCK,
) -> SourceResponsesStream:
    # SSE is also used for downstream non-stream requests. It provides native
    # liveness pings during long thinking without inventing output progress.
    payload = cast(dict[str, JsonValue], {**prepared.body, "stream": True})
    secret = prepared.headers["authorization"].removeprefix("Bearer ")
    try:
        stack, response, _ = await _open_source_stream(
            prepared.source,
            "/v1/messages?beta=true",
            payload,
            encryptor=None,
            prepared_headers=prepared.headers,
            first_frame_deadline_seconds=None,
            scheduler=scheduler,
            clock=clock,
        )
    except ModelSourceForwardingError as exc:
        raise ModelSourceForwardingError(
            status_code=exc.status_code,
            payload=cast(
                dict[str, JsonValue],
                _redact_json_value({**exc.payload, **({"type": "error"} if projection is None else {})}, secret),
            ),
            upstream_status_code=exc.upstream_status_code,
            retry_after=exc.retry_after,
            timeout_phase=exc.timeout_phase,
            upstream_headers=exc.upstream_headers,
        ) from None
    transport = SourceStreamTransport(stack, scheduler=scheduler)
    holder = SourceUsageHolder()
    native_observer = NativeObserver(holder)
    observer = SourceStreamUsageParser(holder, response_shape="responses")
    events = _iter_sse_events(response, source_stream_idle_seconds(), 8 * 1024 * 1024)
    try:
        with scheduler.fail_after(SOURCE_FIRST_FRAME_DEADLINE_SECONDS):
            first = await anext(events)
        holder.first_frame_at = clock.monotonic()
    except BaseException as exc:
        try:
            await events.aclose()
        finally:
            await transport.aclose()
        if isinstance(exc, (TimeoutError, StopAsyncIteration, StreamIdleTimeoutError)):
            raise _failure("invalid_upstream_response", "Claude did not start an SSE response") from exc
        if isinstance(exc, (aiohttp.ClientError, StreamEventTooLargeError)):
            raise _failure("invalid_upstream_response", "Claude SSE response could not be read") from exc
        raise

    async def frames() -> AsyncIterator[bytes]:
        async def native_frames() -> AsyncGenerator[str]:
            yield first
            async for frame in events:
                yield frame

        try:
            async with contextlib.aclosing(native_frames()) as native:
                async for frame in native:
                    event = parse_sse_data_json(frame)
                    if event is None:
                        yield b": keepalive\n\n"
                        continue
                    if event.get("type") == "ping":
                        yield frame.encode() if projection is None else b": keepalive\n\n"
                        continue
                    from pydantic import JsonValue as PydanticJsonValue

                    safe_event = (
                        cast(dict[str, PydanticJsonValue], _redact_json_value(event, secret))
                        if event.get("type") == "error"
                        else cast(dict[str, PydanticJsonValue], event)
                    )
                    if projection is None:
                        native_observer.consume(cast(dict[str, JsonValue], safe_event))
                        yield (
                            format_sse_event(cast(dict[str, JsonValue], safe_event)).encode()
                            if event.get("type") == "error"
                            else frame.encode()
                        )
                        if native_observer.stopped:
                            return
                        continue
                    for converted in projection.consume(safe_event):
                        encoded = format_sse_event(cast(dict[str, JsonValue], converted)).encode()
                        observer.feed(encoded)
                        yield encoded
                    if projection.stopped:
                        return
            raise _failure("model_source_stream_truncated", "Claude stream ended before message_stop")
        except ClaudeError as exc:
            raise _failure("invalid_upstream_response", str(exc)) from exc
        except (ValidationError, StreamEventTooLargeError) as exc:
            raise _failure("invalid_upstream_response", "Claude returned invalid stream metadata") from exc
        except StreamIdleTimeoutError as exc:
            raise _failure("model_source_idle_timeout", "Claude stream exceeded the upstream idle timeout") from exc
        except (aiohttp.ClientError, TimeoutError) as exc:
            raise _failure("model_source_unreachable", "Claude transport failed before completion") from exc
        finally:
            try:
                await events.aclose()
            finally:
                await transport.aclose()

    return SourceResponsesStream(
        body=frames(),
        usage_holder=holder,
        upstream_status_code=response.status,
        transport=transport,
        upstream_headers=public_headers(response.headers),
    )


def public_headers(headers: Mapping[str, str]) -> dict[str, str]:
    return {
        key: value
        for key, value in headers.items()
        if key.lower().startswith("anthropic-ratelimit-") or key.lower() in {"retry-after", "request-id"}
    }


async def forward_native(prepared: PreparedClaudeRequest, *, count_tokens: bool = False) -> SourceResponsesCompletion:
    secret = prepared.headers["authorization"].removeprefix("Bearer ")
    try:
        async with lease_model_source_session() as session:
            async with session.post(
                prepared.url,
                headers=prepared.headers,
                json=prepared.body,
                timeout=_source_client_timeout(prepared.source),
                allow_redirects=False,
            ) as response:
                data = await _response_json(response)
                if data is None:
                    raise _failure("invalid_upstream_response", "Claude returned invalid JSON")
                if response.status >= 400:
                    raise ModelSourceForwardingError(
                        status_code=response.status,
                        payload=cast(dict[str, JsonValue], _redact_json_value(data, secret)),
                        upstream_status_code=response.status,
                        retry_after=response.headers.get("Retry-After"),
                        upstream_headers=public_headers(response.headers),
                    )
                if count_tokens:
                    count = data.get("input_tokens")
                    if not isinstance(count, int) or isinstance(count, bool) or count < 0:
                        raise _failure("invalid_upstream_response", "Claude returned an invalid token count")
                elif (
                    not isinstance(data.get("content"), list)
                    or not isinstance(data.get("stop_reason"), str)
                    or not isinstance(data.get("usage"), dict)
                ):
                    raise _failure("invalid_upstream_response", "Claude returned an invalid Messages response")
                usage = SourceUsage(0, 0) if count_tokens else usage_totals(Usage.model_validate(data.get("usage", {})))
                return SourceResponsesCompletion(
                    data, usage, None, response.status, upstream_headers=public_headers(response.headers)
                )
    except ValidationError as exc:
        raise _failure("invalid_upstream_response", "Claude returned invalid usage metadata") from exc
    except (aiohttp.ClientError, TimeoutError) as exc:
        raise _failure("model_source_unreachable", "Claude transport failed") from exc
