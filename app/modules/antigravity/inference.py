"""Responses orchestration for Antigravity at the shared source-dispatch boundary.

One prepared request is one upstream send: account selection and stickiness, a
credential snapshot, the client identity, the Gemini translation and the native
Cloud Code envelope (agy 1.4.10 capture).
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from typing import cast

from pydantic import JsonValue as PydanticJsonValue

from app.core.crypto import TokenEncryptor
from app.core.openai.exceptions import ClientPayloadError
from app.core.openai.reasoning import ANTIGRAVITY_REASONING_PREFIX
from app.core.types import JsonValue
from app.core.utils.sse import parse_sse_data_json
from app.db.models import ModelSource
from app.db.session import detach_session_objects, get_background_session
from app.modules.antigravity.auth import AntigravityAuth
from app.modules.antigravity.catalog import wire_model
from app.modules.antigravity.client import native_headers
from app.modules.antigravity.errors import AntigravityError
from app.modules.antigravity.opaque import AntigravityOpaqueState, ThoughtScope
from app.modules.antigravity.protocol import project_responses
from app.modules.antigravity.quota import plan_type
from app.modules.antigravity.recovery import RecoveryState
from app.modules.antigravity.repository import AntigravityRepository
from app.modules.antigravity.responses import GeminiProjection, Usage
from app.modules.antigravity.routing import catalog_family, claim_session, select_account
from app.modules.antigravity.schemas import AccountState, CatalogFamily, Effort
from app.modules.antigravity.tool_names import GoogleToolNames
from app.modules.antigravity.version import AntigravityVersionService, ClientIdentity
from app.modules.api_keys.service import ApiKeyData
from app.modules.claude.replay import project_foreign_replay
from app.modules.model_sources.continuation import SourceContinuation
from app.modules.model_sources.forwarding import (
    ModelSourceForwardingError,
    SourceResponsesCompletion,
    SourceResponsesStream,
)

_CASCADE_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "codex-lb:antigravity:cascade")


@dataclass(frozen=True)
class PreparedAntigravityRequest:
    source: ModelSource
    family: CatalogFamily
    wire_model: str
    effort: Effort | None
    requested_effort: str | None
    plan_type: str
    project_id: str
    credential_generation: int
    access_token: str = field(repr=False)
    identity: ClientIdentity
    envelope: dict[str, JsonValue]
    scope: ThoughtScope
    tools: GoogleToolNames
    show_summary: bool
    model: str

    @property
    def headers(self) -> dict[str, str]:
        return native_headers(self.access_token, self.identity)

    def projection(self, opaque: AntigravityOpaqueState, *, prior: Usage | None = None) -> GeminiProjection:
        carried = prior or Usage()
        return GeminiProjection(
            self.model, self.scope, self.tools, opaque, self.show_summary, usage=carried, prior=carried
        )


@dataclass(frozen=True)
class AntigravityAttempt:
    prepared: PreparedAntigravityRequest
    opaque: AntigravityOpaqueState


def cascade_id(client_scope: str, conversation_id: str) -> str:
    """The conversation's stable native cascade; never derived from prompt text."""
    return str(uuid.uuid5(_CASCADE_NAMESPACE, json.dumps([client_scope, conversation_id])))


def _is_turn_start(content: dict[str, JsonValue]) -> bool:
    parts = content.get("parts")
    return (
        content.get("role") == "user"
        and isinstance(parts, list)
        and not any(isinstance(part, dict) and "functionResponse" in part for part in parts)
    )


def envelope(
    request: dict[str, JsonValue],
    *,
    family: CatalogFamily,
    wire: str,
    project_id: str,
    session_id: str,
    cascade: str,
    used_claude: bool,
) -> dict[str, JsonValue]:
    """The native agent envelope; key order, label set and string label values follow the CLI capture.

    `used_claude` is installation history, not the current model: the CLI reports false on its first
    Claude turn and true afterwards, in any cascade. `used_non_gemini_model` is true on every captured
    agent request, Gemini included, because each CLI turn first sends a checkpoint request on a Claude model.
    """
    contents = cast(list[dict[str, JsonValue]], request["contents"])
    starts = [index for index, content in enumerate(contents) if _is_turn_start(content)]
    turn_start = starts[-1] if starts else 0
    # Model steps since the turn's user message; tool results are their own (model or user) steps.
    sent = sum(
        1
        for content in contents[turn_start + 1 :]
        if content.get("role") == "model"
        and not any(
            isinstance(part, dict) and "functionResponse" in part for part in cast(list[JsonValue], content["parts"])
        )
    )
    trajectory = str(uuid.uuid5(uuid.UUID(cascade), f"turn:{len(starts)}"))
    last_step = len(contents) - 1
    claude_history = "true" if used_claude else "false"
    labels: dict[str, JsonValue] = {
        "cascade_id": cascade,
        "last_step_index": str(last_step),
        "model_enum": family.model_enums.get(wire, ""),
        "request_id": f"{trajectory}-{sent}",
        "root_cascade_id": cascade,
        "trajectory_id": trajectory,
        "used_claude": claude_history,
        "used_claude_conservative": claude_history,
        "used_non_gemini_model": "true",
    }
    inner: dict[str, JsonValue] = {"contents": request["contents"]}
    for key in ("systemInstruction", "tools", "toolConfig"):
        if key in request:
            inner[key] = request[key]
    inner["labels"] = labels
    inner["generationConfig"] = request["generationConfig"]
    inner["sessionId"] = session_id
    return {
        "project": project_id,
        "requestId": f"agent/{cascade}/{int(time.time() * 1000)}/{trajectory}/{last_step + 1}",
        "request": inner,
        "model": wire,
        "userAgent": "antigravity",
        "requestType": "agent",
    }


def _mark_used_claude(state: AccountState) -> AccountState | None:
    return None if state.used_claude else state.model_copy(update={"used_claude": True})


async def prepare_responses(
    payload: dict[str, JsonValue],
    api_key: ApiKeyData | None,
    continuation: SourceContinuation,
    recovery: RecoveryState,
    *,
    chat_reasoning: bool = False,
    require_complete_history: bool = False,
) -> AntigravityAttempt:
    model = payload.get("model")
    if not isinstance(model, str):
        raise ClientPayloadError("Antigravity model is required", param="model")
    conversation_id = continuation.scope.conversation_id
    client_scope = api_key.id if api_key else "anonymous"
    reasoning = payload.get("reasoning")
    requested = reasoning.get("effort") if isinstance(reasoning, dict) else None
    requested_effort = requested if isinstance(requested, str) else None
    logical = project_foreign_replay(
        cast(dict[str, PydanticJsonValue], payload),
        require_complete_history=require_complete_history,
        native_prefix=ANTIGRAVITY_REASONING_PREFIX,
        provider="antigravity",
    )
    opaque = AntigravityOpaqueState(TokenEncryptor())
    async with get_background_session() as session:
        account = await select_account(
            session,
            model,
            api_key,
            conversation_id=conversation_id,
            excluded_source_ids=frozenset(recovery.excluded),
            preferred_source_id=recovery.retry_source_id,
        )
        family = catalog_family(account, model)
        assert family is not None  # Eligibility requires the catalog family.
        selected = next(row for row in account.source.models if row.model == model)
        assert selected.max_output_tokens is not None  # Only resolved catalog models are enabled.
        rejected = recovery.rejected_token if recovery.retry_source_id == account.source_id else None
        snapshot = await AntigravityAuth(AntigravityRepository(session), TokenEncryptor()).snapshot(
            account.source_id, rejected_token=rejected
        )
        if snapshot.project_id is None:
            raise AntigravityError(
                "Antigravity account has no Cloud Code project yet; refresh the account",
                code="antigravity_project_missing",
                status_code=503,
            )
        identity = await AntigravityVersionService(session).snapshot()
        state = AccountState.model_validate_json(account.state_json)
        wire, effort = wire_model(family, requested_effort)
        scope = ThoughtScope(account.source_id, snapshot.project_id, family.id, family.anthropic_wire, client_scope)
        projection = project_responses(
            logical,
            family=family,
            max_output_tokens=selected.max_output_tokens,
            scope=scope,
            opaque=opaque,
            restore_signatures=not recovery.unsigned,
        )
        body = envelope(
            cast(dict[str, JsonValue], projection.request),
            family=family,
            wire=wire,
            project_id=snapshot.project_id,
            session_id=account.session_id,
            cascade=cascade_id(client_scope, conversation_id),
            used_claude=state.used_claude,
        )
        if family.anthropic_wire:
            await AntigravityRepository(session).mutate_state(account.source_id, snapshot.generation, _mark_used_claude)
        await claim_session(session, client_scope, conversation_id, account.source_id)
        await session.commit()
        source = account.source
        detach_session_objects(session)
    recovery.bind(account.source_id, snapshot.generation, snapshot.access_token, family.quota_family, family.id)
    continuation.source_id = source.id
    summary = reasoning.get("summary") if isinstance(reasoning, dict) else None
    display = reasoning.get("display") if isinstance(reasoning, dict) else None
    return AntigravityAttempt(
        PreparedAntigravityRequest(
            source=source,
            family=family,
            wire_model=wire,
            effort=effort,
            requested_effort=requested_effort,
            plan_type=plan_type(state.subscription),
            project_id=snapshot.project_id,
            credential_generation=snapshot.generation,
            access_token=snapshot.access_token,
            identity=identity,
            envelope=body,
            scope=scope,
            tools=projection.tools,
            show_summary=(summary not in (None, "none")) or (chat_reasoning and display != "omitted"),
            model=model,
        ),
        opaque,
    )


async def collect_response(stream: SourceResponsesStream) -> SourceResponsesCompletion:
    """Non-stream clients: the adapter's own SSE collected into the terminal response."""
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
        if terminal is None:
            raise ModelSourceForwardingError(
                status_code=502,
                payload={
                    "error": {
                        "type": "upstream_error",
                        "code": "model_source_stream_truncated",
                        "message": "Antigravity ended without a terminal response",
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
