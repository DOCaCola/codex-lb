"""Authenticated history provenance and target-specific Responses projection."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from pydantic import JsonValue

from app.core.openai.exceptions import ClientPayloadError
from app.core.openai.reasoning import CLAUDE_REASONING_PREFIX, append_reasoning_summary
from app.core.types import JsonValue as NativeJsonValue
from app.modules.claude.opaque import ClaudeOpaqueState, SignedBlock
from app.modules.claude.search import assistant_history_message, claude_search_text, openai_search_text, search_replay
from app.modules.claude.task_input import is_external_task_input
from app.modules.model_sources.compaction import source_compaction_history

logger = logging.getLogger(__name__)


def _last_user_index(items: list[JsonValue]) -> int:
    # Task envelopes are user turns; paired tool outputs are not.
    return max(
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


def _active_turn_start(items: list[JsonValue], *, compaction: bool) -> int:
    """Index from which reasoning belongs to the turn Claude continues."""
    if not compaction:
        return _last_user_index(items)
    # The summarizer instruction is not a client turn. Compacting a turn that
    # ended with an assistant message is equivalent to starting a new one.
    history = source_compaction_history(items)
    final = history[-1] if history else None
    if isinstance(final, dict) and final.get("role") == "assistant" and final.get("type", "message") == "message":
        return len(history)
    return _last_user_index(history)


def project_foreign_replay(
    payload: dict[str, JsonValue], *, require_complete_history: bool = False
) -> dict[str, JsonValue]:
    """Preserve portable reasoning without treating foreign ciphertext as Claude state."""
    items = payload.get("input")
    if not isinstance(items, list):
        return payload
    active_start = _active_turn_start(items, compaction=require_complete_history)
    projected: list[JsonValue] = []
    converted = 0
    omitted = 0
    active = 0
    for index, item in enumerate(items):
        if not isinstance(item, dict) or item.get("type") != "reasoning":
            projected.append(item)
            continue
        param = f"input[{index}]"
        token = item.get("encrypted_content")
        if token is not None and not isinstance(token, str):
            raise ClientPayloadError(
                "Reasoning encrypted_content must be text", param=param, code="invalid_provider_history"
            )
        if isinstance(token, str) and token.startswith(CLAUDE_REASONING_PREFIX):
            projected.append(item)
            continue
        texts: list[str] = []
        for field, kind in (("summary", "summary_text"), ("content", "reasoning_text")):
            parts = item.get(field)
            if parts is None:
                continue
            if not isinstance(parts, list):
                raise ClientPayloadError(
                    f"Reasoning {field} must be an array", param=f"{param}.{field}", code="invalid_provider_history"
                )
            field_texts: list[str] = []
            for part in parts:
                if not isinstance(part, dict) or part.get("type") != kind or not isinstance(part.get("text"), str):
                    raise ClientPayloadError(
                        f"Reasoning {field} cannot be represented as assistant text",
                        param=f"{param}.{field}",
                        code="nonportable_provider_history",
                    )
                text = part["text"]
                assert isinstance(text, str)
                if text.strip():
                    field_texts.append(text)
            # Some clients mirror the same text into summary and content.
            if field == "summary" or field_texts != texts:
                texts.extend(field_texts)
        if texts:
            projected.append(
                {
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": text} for text in texts],
                }
            )
        else:
            # Keep item positions stable for subsequent signed-history diagnostics.
            # Foreign private state has no Claude wire representation;
            # the original encrypted item remains in retained logical history.
            projected.append({"type": "reasoning", "summary": []})
        if token and not texts:
            omitted += 1
        else:
            converted += 1
        if index >= active_start:
            active += 1
    if not converted and not omitted:
        return payload
    logger.info("claude_foreign_history_projection converted=%d omitted=%d active=%d", converted, omitted, active)
    return {**payload, "input": projected}


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
) -> list[NativeJsonValue]:
    """Translate Claude state for OpenAI; never relabel opaque Claude state as OpenAI."""
    envelopes: dict[int, SignedBlock] = {}
    # Search call item ID -> (envelope index, readable projection).
    searches: dict[str, tuple[int, str]] = {}
    for index, item in enumerate(items):
        token = item.get("encrypted_content") if isinstance(item, dict) else None
        if not isinstance(token, str) or not token.startswith(CLAUDE_REASONING_PREFIX):
            continue
        param = f"input[{index}]"
        try:
            envelope = opaque.authenticate(token, client_scope=client_scope)
        except ClientPayloadError as exc:
            raise ClientPayloadError(str(exc), param=param, code="invalid_provider_history") from exc
        assert isinstance(item, dict)
        if item.get("type") != "reasoning":
            raise ClientPayloadError(
                "Claude reasoning envelope must belong to a reasoning item",
                param=param,
                code="invalid_provider_history",
            )
        if envelope.block["type"] == "web_search":
            item_id, blocks = search_replay(envelope.block)
            searches[item_id] = (index, claude_search_text(blocks))
        envelopes[index] = envelope
    projected: list[NativeJsonValue] = []
    converted = omitted = searched = 0
    for index, item in enumerate(items):
        envelope = envelopes.get(index)
        if envelope is None:
            call_id = item.get("id") if isinstance(item, dict) and item.get("type") == "web_search_call" else None
            if isinstance(call_id, str) and call_id in searches:
                projected.append(assistant_history_message(searches.pop(call_id)[1]))
                searched += 1
            else:
                projected.append(item)
            continue
        kind = envelope.block["type"]
        # Redacted thinking has no readable content; search state travels as its call's projection.
        if kind == "redacted_thinking":
            omitted += 1
            continue
        if kind == "web_search":
            continue
        assert isinstance(item, dict)
        param = f"input[{index}]"
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
    if searches:
        raise ClientPayloadError(
            "Claude search state has no matching search item",
            param=f"input[{min(position for position, _ in searches.values())}]",
            code="invalid_provider_history",
        )
    if converted or omitted or searched:
        logger.info(
            "claude_native_history_projection converted=%d redacted_omitted=%d search_projected=%d",
            converted,
            omitted,
            searched,
        )
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
    # Summarization reads completed thinking that cannot keep its signature.
    readable_history: bool

    def project(self, payload: dict[str, JsonValue], *, source_id: str, model: str) -> dict[str, JsonValue]:
        items = payload.get("input")
        if not isinstance(items, list):
            return payload
        replaced: dict[int, JsonValue | None] = {}
        converted = omitted = searched = 0
        # Claude search calls replayed natively, and projections of those that cannot be.
        native_searches: set[str] = set()
        foreign_searches: dict[str, str] = {}
        for block in self.blocks:
            envelope = block.envelope
            search = envelope.block["type"] == "web_search"
            if (envelope.source_id, envelope.model) == (source_id, model):
                if search:
                    native_searches.add(search_replay(envelope.block)[0])
                continue
            if block.strict:
                raise ClientPayloadError(
                    "Active Claude reasoning or search requires its original account/model", param="input"
                )
            if search:
                item_id, blocks = search_replay(envelope.block)
                foreign_searches[item_id] = claude_search_text(blocks)
                replaced[block.index] = None
                continue
            text = envelope.block.get("thinking") if envelope.block["type"] == "thinking" else None
            assert text is None or isinstance(text, str)
            if self.readable_history and text:
                replaced[block.index] = assistant_history_message(text)
                converted += 1
            else:
                replaced[block.index] = None
                omitted += 1
        for index, item in enumerate(items):
            if not isinstance(item, dict) or item.get("type") != "web_search_call":
                continue
            call_id = item.get("id")
            if isinstance(call_id, str) and call_id in native_searches:
                continue
            # Calls without a Claude envelope come from another provider (OpenAI hosted search).
            text = (
                foreign_searches.pop(call_id)
                if isinstance(call_id, str) and call_id in foreign_searches
                else openai_search_text(item)
            )
            replaced[index] = assistant_history_message(text)
            searched += 1
        if foreign_searches:
            raise ClientPayloadError("Claude search state has no matching search item", param="input")
        if not replaced:
            return payload
        logger.info(
            "claude_reasoning_projection converted=%d omitted=%d search_projected=%d",
            converted,
            omitted,
            searched,
        )
        projected: list[JsonValue] = []
        for index, item in enumerate(items):
            if index not in replaced:
                projected.append(item)
            elif (text_item := replaced[index]) is not None:
                projected.append(text_item)
        return {**payload, "input": projected}


def authenticate_replay(
    payload: dict[str, JsonValue],
    opaque: ClaudeOpaqueState,
    *,
    model: str,
    client_scope: str,
    require_complete_history: bool = False,
) -> ClaudeReplay:
    items = payload.get("input")
    if not isinstance(items, list):
        return ClaudeReplay((), None, None, require_complete_history)
    active_start = _active_turn_start(items, compaction=require_complete_history)
    blocks: list[ReplayBlock] = []
    owner: str | None = None
    preferred: str | None = None
    for index, item in enumerate(items):
        if not isinstance(item, dict) or item.get("type") != "reasoning":
            continue
        token = item.get("encrypted_content")
        if not isinstance(token, str):
            continue
        try:
            envelope = opaque.authenticate(token, client_scope=client_scope)
        except ClientPayloadError as exc:
            raise ClientPayloadError(str(exc), param=f"input[{index}]", code="invalid_provider_history") from exc
        strict = index >= active_start
        if strict:
            if envelope.model != model:
                raise ClientPayloadError("Active Claude reasoning or search requires its original model", param="input")
            if owner is not None and owner != envelope.source_id:
                raise ClientPayloadError("Active Claude history contains conflicting account owners", param="input")
            owner = envelope.source_id
        elif envelope.model == model:
            preferred = envelope.source_id
        blocks.append(ReplayBlock(index, envelope, strict))
    return ClaudeReplay(tuple(blocks), owner, preferred, require_complete_history)
