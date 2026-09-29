"""Responses orchestration at the shared source-dispatch boundary."""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from pydantic import JsonValue as PydanticJsonValue
from starlette.requests import Request

from app.core.crypto import TokenEncryptor
from app.core.openai.exceptions import ClientPayloadError
from app.core.types import JsonValue
from app.core.utils.sse import parse_sse_data_json
from app.db.session import detach_session_objects, get_background_session
from app.modules.api_keys.service import ApiKeyData
from app.modules.claude.dispatch import ClaudeDispatchPreparer, PreparedClaudeRequest
from app.modules.claude.opaque import ClaudeOpaqueState, OpaqueScope
from app.modules.claude.protocol import project_responses
from app.modules.claude.replay import authenticate_replay
from app.modules.claude.repository import ClaudeRepository
from app.modules.claude.responses import ResponsesProjection
from app.modules.claude.routing import select_account
from app.modules.model_sources.continuation import SourceContinuation
from app.modules.model_sources.forwarding import (
    ModelSourceForwardingError,
    SourceResponsesCompletion,
    SourceResponsesStream,
)


@dataclass(frozen=True)
class ClaudeAttempt:
    prepared: PreparedClaudeRequest
    response: ResponsesProjection | None


async def prepare_responses(
    request: Request,
    payload: dict[str, JsonValue],
    api_key: ApiKeyData | None,
    continuation: SourceContinuation,
    *,
    excluded_source_ids: frozenset[str] = frozenset(),
    retry_source_id: str | None = None,
) -> ClaudeAttempt:
    model = payload.get("model")
    if not isinstance(model, str):
        raise ClientPayloadError("Claude model is required", param="model")
    conversation_id = continuation.scope.conversation_id
    client_scope = api_key.id if api_key else "anonymous"
    opaque = ClaudeOpaqueState(TokenEncryptor())
    logical = cast(dict[str, PydanticJsonValue], payload)
    replay = authenticate_replay(
        logical, opaque, model=model, client_scope=client_scope, conversation_id=conversation_id
    )
    async with get_background_session() as session:
        account = await select_account(
            session,
            model,
            api_key,
            conversation_id=conversation_id,
            owner_source_id=replay.owner_source_id or retry_source_id,
            preferred_source_id=replay.preferred_source_id,
            excluded_source_ids=excluded_source_ids,
        )
        selected = next(row for row in account.source.models if row.model == model)
        assert selected.max_output_tokens is not None  # Only resolved catalog models are eligible.
        projection = project_responses(
            replay.project(logical, source_id=account.source_id, model=model),
            max_output_tokens=selected.max_output_tokens,
            restore_reasoning=lambda token: (
                opaque.decode(token, model=model, client_scope=client_scope, conversation_id=conversation_id).block
            ),
        )
        prepared = await ClaudeDispatchPreparer(ClaudeRepository(session)).prepare(
            projection.body,
            api_key,
            conversation_id=conversation_id,
            incoming_headers=request.headers,
            endpoint="messages",
            translated=True,
            owner_source_id=account.source_id,
        )
        detach_session_objects(session)
    continuation.source_id = prepared.source.id
    return ClaudeAttempt(
        prepared,
        ResponsesProjection(
            OpaqueScope(prepared.source.id, model, client_scope, conversation_id),
            projection.tools,
            opaque,
            search_enabled=projection.search_enabled,
        ),
    )


async def collect_response(stream: SourceResponsesStream) -> SourceResponsesCompletion:
    terminal: dict[str, JsonValue] | None = None
    try:
        async for frame in stream.body:
            event = parse_sse_data_json(frame.decode())
            if event is None:
                continue
            if event.get("type") in ("response.completed", "response.incomplete"):
                response = event.get("response")
                if isinstance(response, dict):
                    terminal = response
            elif event.get("type") in ("error", "response.failed"):
                raise ModelSourceForwardingError(
                    status_code=502, payload=event, upstream_status_code=stream.upstream_status_code
                )
        if terminal is None:
            raise ModelSourceForwardingError(
                status_code=502,
                payload={
                    "error": {
                        "code": "model_source_stream_truncated",
                        "message": "Claude ended without a terminal response",
                    }
                },
            )
        return SourceResponsesCompletion(
            terminal,
            stream.usage_holder.usage,
            stream.usage_holder.timings,
            stream.upstream_status_code,
            upstream_headers=stream.upstream_headers,
        )
    finally:
        await stream.aclose()
