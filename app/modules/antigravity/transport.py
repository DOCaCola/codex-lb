"""Cloud Code SSE transport on the shared source connection owner.

Generated events are held until the response shows visible text or a call. A
generation that finishes without either is resent once on the same account
before anything reached the client; the client receives keepalive comments
meanwhile, and both attempts' usage is billed with the response.

A round that only called search_web is answered by the gateway on the same
account; the response then continues with the next upstream round.
"""

from __future__ import annotations

import contextlib
import logging
from collections.abc import AsyncGenerator, AsyncIterator
from contextlib import AsyncExitStack
from typing import cast

import aiohttp
from pydantic import JsonValue as PydanticJsonValue

from app.core.clients.proxy import _iter_sse_events
from app.core.clients.stream_errors import StreamEventTooLargeError, StreamIdleTimeoutError
from app.core.clock import REAL_CLOCK, REAL_SCHEDULER, Clock, Scheduler
from app.core.types import JsonValue
from app.core.utils.sse import format_sse_event, parse_sse_data_json
from app.modules.antigravity.classify import classify
from app.modules.antigravity.errors import AntigravityError
from app.modules.antigravity.inference import AntigravityAttempt
from app.modules.antigravity.recovery import AntigravityUpstreamError
from app.modules.antigravity.responses import EmptyCompletion
from app.modules.antigravity.search import SearchOutcome, run_search
from app.modules.claude.credentials import ClaudeError
from app.modules.model_sources.forwarding import (
    SOURCE_FIRST_FRAME_DEADLINE_SECONDS,
    ModelSourceForwardingError,
    SourceResponsesStream,
    SourceStreamTransport,
    SourceStreamUsageParser,
    SourceUsageHolder,
    _open_source_stream,
    source_stream_idle_seconds,
)

logger = logging.getLogger(__name__)

STREAM_PATH = "/v1internal:streamGenerateContent?alt=sse"
MAX_EVENT_BYTES = 8 * 1024 * 1024
KEEPALIVE_SECONDS = 5.0


def _failure(code: str, message: str) -> ModelSourceForwardingError:
    return ModelSourceForwardingError(
        status_code=502, payload={"error": {"type": "upstream_error", "code": code, "message": message}}
    )


def _stream_error(event: dict[str, JsonValue], secret: str) -> AntigravityUpstreamError:
    """An error line inside the SSE body, classified like an HTTP rejection."""
    error = event.get("error")
    code = error.get("code") if isinstance(error, dict) else None
    status = code if isinstance(code, int) and not isinstance(code, bool) else 500
    return AntigravityUpstreamError(classify(status, event), secret=secret, retry_after=None)


class _Upstream:
    """The open upstream response; replaced by the empty-completion resend."""

    def __init__(self, attempt: AntigravityAttempt, *, scheduler: Scheduler, clock: Clock) -> None:
        self.attempt = attempt
        self.scheduler = scheduler
        self.clock = clock
        self.stack: AsyncExitStack | None = None
        self.status = 200
        # The round being sent; later rounds of the response replace it.
        self.envelope = attempt.prepared.envelope

    async def open(self) -> AsyncGenerator[str]:
        prepared = self.attempt.prepared
        try:
            stack, response, _ = await _open_source_stream(
                prepared.source,
                STREAM_PATH,
                self.envelope,
                encryptor=None,
                prepared_headers=prepared.headers,
                first_frame_deadline_seconds=None,
                compact_json=True,
                scheduler=self.scheduler,
                clock=self.clock,
            )
        except ModelSourceForwardingError as exc:
            if exc.upstream_status_code is None or exc.upstream_status_code < 400:
                raise
            raise AntigravityUpstreamError(
                classify(exc.upstream_status_code, exc.payload),
                secret=prepared.access_token,
                retry_after=exc.retry_after,
            ) from None
        self.stack = stack
        self.status = response.status
        return _iter_sse_events(response, source_stream_idle_seconds(), MAX_EVENT_BYTES)

    async def aclose(self) -> None:
        stack, self.stack = self.stack, None
        if stack is not None:
            await stack.aclose()


async def _first_event(events: AsyncGenerator[str], secret: str) -> dict[str, JsonValue]:
    """The first data line; an error line here is a rejection the recovery loop may still act on."""
    while True:
        frame = await anext(events)
        event = parse_sse_data_json(frame)
        if event is None:
            continue
        if "error" in event:
            raise _stream_error(event, secret)
        return event


async def open_responses(
    attempt: AntigravityAttempt, *, scheduler: Scheduler = REAL_SCHEDULER, clock: Clock = REAL_CLOCK
) -> SourceResponsesStream:
    prepared = attempt.prepared
    secret = prepared.access_token
    started_at = clock.monotonic()
    holder = SourceUsageHolder()
    observer = SourceStreamUsageParser(holder, response_shape="responses", clock=clock, started_at=started_at)
    upstream = _Upstream(attempt, scheduler=scheduler, clock=clock)
    outer = AsyncExitStack()
    outer.push_async_callback(upstream.aclose)
    transport = SourceStreamTransport(outer, scheduler=scheduler)
    try:
        events = await upstream.open()
        with scheduler.fail_after(SOURCE_FIRST_FRAME_DEADLINE_SECONDS):
            first = await _first_event(events, secret)
        holder.first_frame_at = clock.monotonic()
    except BaseException as exc:
        await transport.aclose()
        if isinstance(exc, (TimeoutError, StopAsyncIteration, StreamIdleTimeoutError)):
            raise _failure("invalid_upstream_response", "Antigravity did not start an SSE response") from exc
        if isinstance(exc, (aiohttp.ClientError, StreamEventTooLargeError)):
            raise _failure("invalid_upstream_response", "Antigravity SSE response could not be read") from exc
        raise

    async def lines(
        source: AsyncGenerator[str], opening: dict[str, JsonValue] | None
    ) -> AsyncGenerator[dict[str, JsonValue]]:
        if opening is not None:
            yield opening
        async for frame in source:
            event = parse_sse_data_json(frame)
            if event is None:
                continue
            if "error" in event:
                raise _stream_error(event, secret)
            yield event

    async def frames() -> AsyncIterator[bytes]:
        nonlocal events
        projection = prepared.projection(attempt.opaque)
        held: list[bytes] = []
        released = False
        resent = False
        opening: dict[str, JsonValue] | None = first
        last_signal = clock.monotonic()
        executed = 0
        try:
            while True:
                try:
                    async with contextlib.aclosing(lines(events, opening)) as source:
                        async for line in source:
                            for converted in projection.consume(cast(dict[str, PydanticJsonValue], line)):
                                encoded = format_sse_event(cast(dict[str, JsonValue], converted)).encode()
                                observer.feed(encoded)
                                if released:
                                    yield encoded
                                else:
                                    held.append(encoded)
                            if not released and (projection.visible or projection.stopped):
                                released = True
                                for encoded in held:
                                    yield encoded
                                held.clear()
                            elif not released and clock.monotonic() - last_signal >= KEEPALIVE_SECONDS:
                                last_signal = clock.monotonic()
                                yield b": keepalive\n\n"
                            if projection.stopped:
                                break
                        else:
                            raise _failure(
                                "model_source_stream_truncated", "Antigravity stream ended without a finish reason"
                            )
                    if not projection.awaiting_search:
                        return
                    context = prepared.search
                    assert context is not None  # search_web is declared only with a search context.
                    outcomes: list[SearchOutcome] = []
                    for call in projection.pending_searches():
                        outcomes.append(await run_search(context, call, allowed=executed < context.policy.max_uses))
                        executed += 1
                    for converted in projection.complete_searches(outcomes):
                        encoded = format_sse_event(cast(dict[str, JsonValue], converted)).encode()
                        observer.feed(encoded)
                        yield encoded
                    if projection.stopped:
                        return
                    await upstream.aclose()
                    upstream.envelope = attempt.continuation(list(projection.outputs.values()))
                    events = await upstream.open()
                    opening = None
                except EmptyCompletion:
                    if resent or released:
                        raise _failure(
                            "empty_completion", "Antigravity finished twice without visible output or a tool call"
                        ) from None
                    resent = True
                    logger.info(
                        "antigravity_empty_completion_retry source_id=%s model=%s", prepared.source.id, prepared.model
                    )
                    held.clear()
                    prior = projection.usage
                    await upstream.aclose()
                    events = await upstream.open()
                    opening = None
                    projection = prepared.projection(attempt.opaque, prior=prior)
        except ModelSourceForwardingError:
            if released:
                for converted in projection.interrupt():
                    encoded = format_sse_event(cast(dict[str, JsonValue], converted)).encode()
                    observer.feed(encoded)
                    yield encoded
            raise
        except AntigravityError as exc:
            raise _failure(exc.code, str(exc)) from exc
        except ClaudeError as exc:
            # The shared code-mode helper recovery rejected a call's input.
            raise _failure("invalid_upstream_response", str(exc)) from exc
        except (StreamEventTooLargeError, ValueError) as exc:
            raise _failure("invalid_upstream_response", "Antigravity returned an invalid stream") from exc
        except StreamIdleTimeoutError as exc:
            raise _failure(
                "model_source_idle_timeout", "Antigravity stream exceeded the upstream idle timeout"
            ) from exc
        except (aiohttp.ClientError, TimeoutError) as exc:
            raise _failure(
                "model_source_unreachable", f"Antigravity transport failed before completion: {type(exc).__name__}"
            ) from exc
        finally:
            observer.end_timing()
            await transport.aclose()

    return SourceResponsesStream(
        body=frames(),
        usage_holder=holder,
        upstream_status_code=upstream.status,
        transport=transport,
        timing_observer=observer,
    )
