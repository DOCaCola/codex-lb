"""Authenticated history provenance and target-specific Responses projection."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from pydantic import JsonValue

from app.core.openai.exceptions import ClientPayloadError
from app.core.openai.reasoning import CLAUDE_REASONING_PREFIX, append_reasoning_summary
from app.core.types import JsonValue as NativeJsonValue
from app.modules.claude.opaque import ClaudeOpaqueState, SignedBlock
from app.modules.claude.task_input import is_external_task_input

logger = logging.getLogger(__name__)


def has_claude_replay(items: NativeJsonValue) -> bool:
    return isinstance(items, list) and any(
        isinstance(item, dict)
        and isinstance(token := item.get("encrypted_content"), str)
        and token.startswith(CLAUDE_REASONING_PREFIX)
        for item in items
    )


def project_native_replay(
    items: list[NativeJsonValue],
    opaque: ClaudeOpaqueState,
    *,
    client_scope: str,
    conversation_id: str,
) -> list[NativeJsonValue]:
    """Extract portable thinking, never relabel opaque Claude state as OpenAI."""
    projected: list[NativeJsonValue] = []
    converted = 0
    for index, item in enumerate(items):
        token = item.get("encrypted_content") if isinstance(item, dict) else None
        if not isinstance(token, str) or not token.startswith(CLAUDE_REASONING_PREFIX):
            projected.append(item)
            continue
        param = f"input[{index}]"
        try:
            envelope = opaque.authenticate(token, client_scope=client_scope, conversation_id=conversation_id)
        except ClientPayloadError as exc:
            raise ClientPayloadError(str(exc), param=param, code="invalid_provider_history") from exc
        kind = envelope.block["type"]
        assert isinstance(item, dict)
        if item.get("type") != "reasoning":
            raise ClientPayloadError(
                "Claude reasoning envelope must belong to a reasoning item",
                param=param,
                code="invalid_provider_history",
            )
        if kind != "thinking":
            raise ClientPayloadError(
                "Claude redacted thinking or hosted search state cannot be replayed to OpenAI; "
                "continue with its original Claude model or provide portable context.",
                param=param,
                code="nonportable_provider_history",
            )
        text = envelope.block.get("thinking")
        if not isinstance(text, str):
            raise ClientPayloadError("Invalid Claude thinking text", param=param, code="invalid_provider_history")
        result = dict(item)
        result.pop("id", None)
        result.pop("encrypted_content")
        result.setdefault("summary", [])
        if text:
            append_reasoning_summary(result, text)
        projected.append(result)
        converted += 1
    if converted:
        logger.info("claude_native_history_projection converted=%d", converted)
    return projected


@dataclass(frozen=True)
class ReplayBlock:
    index: int
    envelope: SignedBlock
    strict: bool


@dataclass(frozen=True)
class ClaudeReplay:
    blocks: tuple[ReplayBlock, ...]
    owner_source_id: str | None
    preferred_source_id: str | None

    def project(self, payload: dict[str, JsonValue], *, source_id: str, model: str) -> dict[str, JsonValue]:
        omitted: set[int] = set()
        for block in self.blocks:
            envelope = block.envelope
            if (envelope.source_id, envelope.model) == (source_id, model):
                continue
            if block.strict:
                raise ClientPayloadError(
                    "Active Claude reasoning or search requires its original account/model", param="input"
                )
            omitted.add(block.index)
        if not omitted:
            return payload
        items = payload["input"]
        assert isinstance(items, list)
        logger.info("claude_reasoning_projection reason=route_changed omitted=%d", len(omitted))
        return {**payload, "input": [item for index, item in enumerate(items) if index not in omitted]}


def authenticate_replay(
    payload: dict[str, JsonValue],
    opaque: ClaudeOpaqueState,
    *,
    model: str,
    client_scope: str,
    conversation_id: str,
    require_complete_history: bool = False,
) -> ClaudeReplay:
    items = payload.get("input")
    if not isinstance(items, list):
        return ClaudeReplay((), None, None)
    # Canonical task envelopes are user turns, not paired tool outputs. Actual
    # tool results, including parallel results, remain in the assistant turn.
    last_user = max(
        (
            index
            for index, item in enumerate(items)
            if isinstance(item, dict)
            and (
                (item.get("role") == "user" and item.get("type", "message") == "message")
                or is_external_task_input(item)
            )
        ),
        default=-1,
    )
    blocks: list[ReplayBlock] = []
    owner: str | None = None
    preferred: str | None = None
    for index, item in enumerate(items):
        if not isinstance(item, dict) or item.get("type") != "reasoning":
            continue
        token = item.get("encrypted_content")
        if not isinstance(token, str):
            continue
        envelope = opaque.authenticate(token, client_scope=client_scope, conversation_id=conversation_id)
        # Summarization must not silently discard even completed signed history
        # when the preferred account/model is unavailable.
        strict = require_complete_history or envelope.block.get("type") == "web_search" or index >= last_user
        if strict:
            if envelope.model != model:
                raise ClientPayloadError(
                    "Claude compaction requires its original model for signed history"
                    if require_complete_history
                    else "Active Claude reasoning or search requires its original model",
                    param="input",
                )
            if owner is not None and owner != envelope.source_id:
                raise ClientPayloadError(
                    "Claude compaction contains conflicting signed history owners"
                    if require_complete_history
                    else "Active Claude history contains conflicting account owners",
                    param="input",
                )
            owner = envelope.source_id
        elif envelope.model == model:
            preferred = envelope.source_id
        blocks.append(ReplayBlock(index, envelope, strict))
    return ClaudeReplay(tuple(blocks), owner, preferred)
