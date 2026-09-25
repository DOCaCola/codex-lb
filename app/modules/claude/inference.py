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
) -> ClaudeAttempt:
    model = payload.get("model")
    if not isinstance(model, str):
        raise ClientPayloadError("Claude model is required", param="model")
    conversation_id = continuation.scope.conversation_id
    client_scope = api_key.id if api_key else "anonymous"
    opaque = ClaudeOpaqueState(TokenEncryptor())
    owner: str | None = None
    restored: dict[str, dict[str, PydanticJsonValue]] = {}
    items = payload.get("input")
    if isinstance(items, list):
        for item in items:
            if not isinstance(item, dict) or item.get("type") != "reasoning":
                continue
            token = item.get("encrypted_content")
            if not isinstance(token, str):
                continue
            block = opaque.decode(token, model=model, client_scope=client_scope, conversation_id=conversation_id)
            if owner is not None and owner != block.source_id:
                raise ClientPayloadError("Claude signed history contains multiple account owners", param="input")
            owner = block.source_id
            restored[token] = block.block
    async with get_background_session() as session:
        account = await select_account(session, model, api_key, conversation_id=conversation_id, owner_source_id=owner)
        selected = next(row for row in account.source.models if row.model == model)
        projection = project_responses(
            cast(dict[str, PydanticJsonValue], payload),
            max_output_tokens=selected.max_output_tokens or 8192,
            restore_reasoning=restored.__getitem__,
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
