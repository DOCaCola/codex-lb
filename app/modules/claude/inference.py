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
from app.modules.claude.chat_replay import ChatHistory, plan_chat_replay
from app.modules.claude.dispatch import ClaudeDispatchPreparer, PreparedClaudeRequest
from app.modules.claude.opaque import ClaudeOpaqueState, OpaqueScope
from app.modules.claude.protocol import project_responses
from app.modules.claude.replay import authenticate_replay
from app.modules.claude.repository import ClaudeRepository
from app.modules.claude.responses import ResponsesProjection
from app.modules.claude.routing import ClaudePoolUnavailable, select_account
from app.modules.claude.schemas import AccountState
from app.modules.claude.service import catalog_reasoning
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
    chat_reasoning: bool = False,
    chat_history: ChatHistory | None = None,
) -> ClaudeAttempt:
    model = payload.get("model")
    if not isinstance(model, str):
        raise ClientPayloadError("Claude model is required", param="model")
    conversation_id = continuation.scope.conversation_id
    client_scope = api_key.id if api_key else "anonymous"
    opaque = ClaudeOpaqueState(TokenEncryptor())
    logical = cast(dict[str, PydanticJsonValue], payload)
    raw_instructions = payload.get("instructions")
    instructions = raw_instructions if isinstance(raw_instructions, str) else ""
    chat_plan = (
        await plan_chat_replay(
            chat_history,
            store=continuation.store,
            scope=continuation.scope,
            opaque=opaque,
            model=model,
            client_scope=client_scope,
            instructions=instructions,
        )
        if chat_history is not None
        else None
    )
    async with get_background_session() as session:
        if chat_plan is not None:
            try:
                account = await select_account(
                    session,
                    model,
                    api_key,
                    conversation_id=conversation_id,
                    owner_source_id=chat_plan.active_owner or retry_source_id,
                    preferred_source_id=chat_plan.preferred_owner,
                    excluded_source_ids=excluded_source_ids,
                )
            except ClaudePoolUnavailable as exc:
                if exc.code != "previous_response_owner_unavailable" or chat_plan.active_owner is None:
                    raise
                account = await select_account(
                    session,
                    model,
                    api_key,
                    conversation_id=conversation_id,
                    preferred_source_id=chat_plan.preferred_owner,
                    excluded_source_ids=excluded_source_ids,
                )
            logical = cast(
                dict[str, PydanticJsonValue],
                {**payload, "input": chat_plan.project(source_id=account.source_id)},
            )
            replay = authenticate_replay(
                logical, opaque, model=model, client_scope=client_scope, conversation_id=conversation_id
            )
        else:
            replay = authenticate_replay(
                logical, opaque, model=model, client_scope=client_scope, conversation_id=conversation_id
            )
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
        projected = replay.project(logical, source_id=account.source_id, model=model)
        if chat_history is not None:
            continuation.payload["input"] = cast(JsonValue, projected["input"])
            continuation.chat_input = chat_history.items
            continuation.chat_instructions = instructions
        projection = project_responses(
            projected,
            max_output_tokens=selected.max_output_tokens,
            reasoning=catalog_reasoning(AccountState.model_validate_json(account.state_json), model),
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
    reasoning = logical.get("reasoning")
    visible_chat_reasoning = chat_reasoning and (
        not isinstance(reasoning, dict) or reasoning.get("display") != "omitted"
    )
    return ClaudeAttempt(
        prepared,
        ResponsesProjection(
            OpaqueScope(prepared.source.id, model, client_scope, conversation_id),
            projection.tools,
            opaque,
            search_enabled=projection.search_enabled,
            chat_reasoning=visible_chat_reasoning,
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
