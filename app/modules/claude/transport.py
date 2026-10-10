"""Bounded Claude SSE transport, using the shared source connection owner."""

from __future__ import annotations

import contextlib
import logging
from collections.abc import AsyncGenerator, AsyncIterator, Mapping
from dataclasses import replace
from datetime import UTC, datetime
from typing import cast

import aiohttp
from pydantic import ValidationError

from app.core.clients.http import lease_model_source_session
from app.core.clients.proxy import _iter_sse_events
from app.core.clients.stream_errors import StreamEventTooLargeError, StreamIdleTimeoutError
from app.core.clock import REAL_CLOCK, REAL_SCHEDULER, Clock, Scheduler
from app.core.types import JsonValue
from app.core.utils.sse import format_sse_event, parse_sse_data_json
from app.modules.claude.cache_lineage import CACHE_LINEAGE
from app.modules.claude.credentials import ClaudeError
from app.modules.claude.dispatch import PreparedClaudeRequest
from app.modules.claude.native import NativeObserver, usage_totals
from app.modules.claude.observations import record_headers
from app.modules.claude.recovery import historical_recovery
from app.modules.claude.refusals import record_refused_response
from app.modules.claude.resources import record_origins
from app.modules.claude.responses import ResponsesProjection, Usage
from app.modules.model_sources.forwarding import (
    SOURCE_FIRST_FRAME_DEADLINE_SECONDS,
    ModelSourceForwardingError,
    SourceResponsesCompletion,
    SourceResponsesStream,
    SourceStreamTransport,
    SourceStreamUsageParser,
    SourceTimings,
    SourceUsage,
    SourceUsageHolder,
    _open_source_stream,
    _redact_json_value,
    _response_json,
    _source_client_timeout,
    source_stream_idle_seconds,
    unreachable_error,
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


logger = logging.getLogger(__name__)


async def open_responses(
    prepared: PreparedClaudeRequest,
    projection: ResponsesProjection | None,
    *,
    scheduler: Scheduler = REAL_SCHEDULER,
    clock: Clock = REAL_CLOCK,
) -> SourceResponsesStream:
    try:
        return await _open_responses(prepared, projection, scheduler=scheduler, clock=clock)
    except ModelSourceForwardingError as exc:
        recovered = historical_recovery(
            cast(dict[str, JsonValue], prepared.body), exc, readable_history=prepared.require_complete_history
        )
        if recovered is None or prepared.budget.remaining == 0:
            raise
    logger.info("claude_signature_recovery source_id=%s attempt=1", prepared.source.id)
    try:
        result = await _open_responses(replace(prepared, body=recovered), projection, scheduler=scheduler, clock=clock)
    except ModelSourceForwardingError:
        logger.info("claude_signature_recovery source_id=%s outcome=rejected", prepared.source.id)
        raise
    logger.info("claude_signature_recovery source_id=%s outcome=stream_opened", prepared.source.id)
    return result


async def _open_responses(
    prepared: PreparedClaudeRequest,
    projection: ResponsesProjection | None,
    *,
    scheduler: Scheduler = REAL_SCHEDULER,
    clock: Clock = REAL_CLOCK,
) -> SourceResponsesStream:
    from app.modules.claude.threads import MessageThread, normalize_thread_error, record_message

    thread = MessageThread.parse(prepared.body) if projection is None else None
    # SSE is also used for downstream non-stream requests. It provides native
    # liveness pings during long thinking without inventing output progress.
    payload = cast(dict[str, JsonValue], {**prepared.body, "stream": True})
    prepared.budget.consume()
    secret = prepared.headers["authorization"].removeprefix("Bearer ")
    requested_at = datetime.now(UTC)
    prepared.budget.requested_at = requested_at
    started_at = clock.monotonic()
    holder = SourceUsageHolder()
    native_timing = SourceStreamUsageParser(holder, response_shape="claude", clock=clock, started_at=started_at)
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
        await record_headers(
            prepared.source.id, prepared.credential_generation, exc.upstream_headers, requested_at=requested_at
        )
        safe_error = ModelSourceForwardingError(
            status_code=exc.status_code,
            payload=cast(
                dict[str, JsonValue],
                _redact_json_value({**exc.payload, **({"type": "error"} if projection is None else {})}, secret),
            ),
            upstream_status_code=exc.upstream_status_code,
            retry_after=exc.retry_after,
            timeout_phase=exc.timeout_phase,
            upstream_headers=exc.upstream_headers,
            pre_dispatch=exc.pre_dispatch,
        )
        raise normalize_thread_error(prepared.body, safe_error) from None
    transport = SourceStreamTransport(stack, scheduler=scheduler)
    native_observer = NativeObserver(holder)
    observer = SourceStreamUsageParser(holder, response_shape="responses")
    events = _iter_sse_events(response, source_stream_idle_seconds(), 8 * 1024 * 1024)
    start_usage: JsonValue = None
    try:
        await record_headers(
            prepared.source.id, prepared.credential_generation, response.headers, requested_at=requested_at
        )
        with scheduler.fail_after(SOURCE_FIRST_FRAME_DEADLINE_SECONDS):
            startup: list[str] = []
            startup_bytes = 0
            while True:
                frame = await anext(events)
                native_timing.feed(frame.encode())
                if holder.first_frame_at is None:
                    holder.first_frame_at = clock.monotonic()
                startup_bytes += len(frame.encode())
                if len(startup) >= 32 or startup_bytes > 64 * 1024:
                    raise _failure("invalid_upstream_response", "Claude SSE startup exceeded its buffer limit")
                startup.append(frame)
                event = parse_sse_data_json(frame)
                if event is None:
                    if all(not line.strip() or line.startswith(":") for line in frame.splitlines()):
                        continue
                    break
                if event.get("type") == "ping":
                    continue
                detail = event.get("error")
                if (
                    event.get("type") == "error"
                    and isinstance(detail, dict)
                    and detail.get("type") == "overloaded_error"
                ):
                    raise ModelSourceForwardingError(
                        status_code=529,
                        upstream_status_code=529,
                        payload=cast(dict[str, JsonValue], _redact_json_value(event, secret)),
                        retry_after=response.headers.get("Retry-After"),
                        upstream_headers=public_headers(response.headers),
                    )
                if event.get("type") == "message_start":
                    message = event.get("message")
                    if isinstance(message, dict):
                        start_usage = message.get("usage")
                    if isinstance(message, dict) and message.get("content", []) == []:
                        usage = message.get("usage", {})
                        if isinstance(usage, dict) and usage.get("output_tokens", 0) == 0:
                            continue
                break
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
    CACHE_LINEAGE.observe(
        conversation_id=prepared.conversation_id,
        session_id=prepared.session_id,
        source_id=prepared.source.id,
        body=prepared.body,
        usage=start_usage,
    )

    async def frames() -> AsyncIterator[bytes]:
        try:
            async with contextlib.aclosing(translated_frames()) as translated:
                async for chunk in translated:
                    yield chunk
        except ModelSourceForwardingError:
            # The client keeps output it saw completed; Claude's finished text closes before the error.
            if projection is not None:
                for converted in projection.interrupt():
                    encoded = format_sse_event(cast(dict[str, JsonValue], converted)).encode()
                    observer.feed(encoded)
                    yield encoded
            raise

    async def translated_frames() -> AsyncGenerator[bytes]:
        async def native_frames() -> AsyncGenerator[str]:
            for frame in startup:
                yield frame
            async for frame in events:
                yield frame

        try:
            startup_remaining = len(startup)
            async with contextlib.aclosing(native_frames()) as native:
                async for frame in native:
                    if startup_remaining:
                        startup_remaining -= 1
                    else:
                        native_timing.feed(frame.encode())
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
                        if prepared.native_binding is not None:
                            if thread is not None and event.get("type") == "message_start":
                                await record_message(
                                    prepared.native_binding.resource_scope, prepared.source.id, safe_event
                                )
                            await record_origins(prepared.native_binding.resource_scope, prepared.source.id, safe_event)
                        yield (
                            format_sse_event(cast(dict[str, JsonValue], safe_event)).encode()
                            if event.get("type") == "error"
                            else frame.encode()
                        )
                        if native_observer.stopped:
                            return
                        continue
                    for converted in projection.consume(safe_event):
                        if converted["type"] == "response.failed" and projection.refused_delivered_output:
                            await record_refused_response(
                                projection.scope.client_scope, projection.response_id, prepared.source.id
                            )
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
            raise _failure(
                "model_source_unreachable", f"Claude transport failed before completion: {type(exc).__name__}"
            ) from exc
        finally:
            native_timing.end_timing()
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
        timing_observer=native_timing,
    )


def public_headers(headers: Mapping[str, str]) -> dict[str, str]:
    return {
        key: value
        for key, value in headers.items()
        if key.lower().startswith("anthropic-ratelimit-") or key.lower() in {"retry-after", "request-id"}
    }


async def forward_native(prepared: PreparedClaudeRequest, *, count_tokens: bool = False) -> SourceResponsesCompletion:
    try:
        return await _forward_native(prepared, count_tokens=count_tokens)
    except ModelSourceForwardingError as exc:
        recovered = (
            None
            if count_tokens
            else historical_recovery(cast(dict[str, JsonValue], prepared.body), exc, readable_history=False)
        )
        if recovered is None or prepared.budget.remaining == 0:
            raise
    logger.info("claude_signature_recovery source_id=%s attempt=1", prepared.source.id)
    try:
        result = await _forward_native(replace(prepared, body=recovered))
    except ModelSourceForwardingError:
        logger.info("claude_signature_recovery source_id=%s outcome=rejected", prepared.source.id)
        raise
    logger.info("claude_signature_recovery source_id=%s outcome=completed", prepared.source.id)
    return result


async def _forward_native(prepared: PreparedClaudeRequest, *, count_tokens: bool = False) -> SourceResponsesCompletion:
    from app.modules.claude.threads import MessageThread, normalize_thread_error, record_message

    thread = MessageThread.parse(prepared.body) if not count_tokens else None
    prepared.budget.consume()
    secret = prepared.headers["authorization"].removeprefix("Bearer ")
    requested_at = datetime.now(UTC)
    prepared.budget.requested_at = requested_at
    started_at = REAL_CLOCK.monotonic()
    try:
        async with lease_model_source_session() as session:
            async with session.post(
                prepared.url,
                headers=prepared.headers,
                json=prepared.body,
                timeout=_source_client_timeout(prepared.source),
                allow_redirects=False,
            ) as response:
                await record_headers(
                    prepared.source.id, prepared.credential_generation, response.headers, requested_at=requested_at
                )
                data = await _response_json(response)
                if data is None:
                    raise _failure("invalid_upstream_response", "Claude returned invalid JSON")
                if response.status >= 400:
                    error = ModelSourceForwardingError(
                        status_code=response.status,
                        payload=cast(dict[str, JsonValue], _redact_json_value(data, secret)),
                        upstream_status_code=response.status,
                        retry_after=response.headers.get("Retry-After"),
                        upstream_headers=public_headers(response.headers),
                    )
                    raise normalize_thread_error(prepared.body, error)
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
                duration_ms = round((REAL_CLOCK.monotonic() - started_at) * 1000)
                content = data.get("content")
                generated = (
                    not count_tokens
                    and isinstance(content, list)
                    and any(
                        isinstance(block, dict)
                        and (
                            bool(block.get("text"))
                            or bool(block.get("thinking"))
                            or (block.get("type") == "tool_use" and bool(block.get("name")))
                        )
                        for block in content
                    )
                )
                if not count_tokens and prepared.native_binding is not None:
                    from pydantic import JsonValue as PydanticJsonValue

                    await record_origins(
                        prepared.native_binding.resource_scope,
                        prepared.source.id,
                        cast(dict[str, PydanticJsonValue], data),
                    )
                    if thread is not None:
                        await record_message(
                            prepared.native_binding.resource_scope,
                            prepared.source.id,
                            cast(dict[str, PydanticJsonValue], data),
                        )
                return SourceResponsesCompletion(
                    data,
                    usage,
                    SourceTimings(duration_ms if generated else None, duration_ms),
                    response.status,
                    upstream_headers=public_headers(response.headers),
                )
    except ValidationError as exc:
        raise _failure("invalid_upstream_response", "Claude returned invalid usage metadata") from exc
    except (aiohttp.ClientError, TimeoutError) as exc:
        raise unreachable_error(prepared.source, exc) from exc
