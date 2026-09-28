"""Authenticated history provenance and target-specific Responses projection."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from pydantic import JsonValue

from app.core.openai.exceptions import ClientPayloadError
from app.modules.claude.opaque import ClaudeOpaqueState, SignedBlock

logger = logging.getLogger(__name__)


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
) -> ClaudeReplay:
    items = payload.get("input")
    if not isinstance(items, list):
        return ClaudeReplay((), None, None)
    # Only a new explicit user turn completes earlier thinking. Tool outputs,
    # including parallel results, are still part of the preceding assistant turn.
    last_user = max(
        (
            index
            for index, item in enumerate(items)
            if isinstance(item, dict) and item.get("role") == "user" and item.get("type", "message") == "message"
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
        strict = envelope.block.get("type") == "web_search" or index >= last_user
        if strict:
            if envelope.model != model:
                raise ClientPayloadError("Active Claude reasoning or search requires its original model", param="input")
            if owner is not None and owner != envelope.source_id:
                raise ClientPayloadError("Active Claude history contains conflicting account owners", param="input")
            owner = envelope.source_id
        elif envelope.model == model:
            preferred = envelope.source_id
        blocks.append(ReplayBlock(index, envelope, strict))
    return ClaudeReplay(tuple(blocks), owner, preferred)
