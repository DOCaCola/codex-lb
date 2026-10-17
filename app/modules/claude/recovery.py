"""Survival of replayed historical thinking: prefix binding and one-shot recovery."""

from __future__ import annotations

import re
from copy import deepcopy

from pydantic import JsonValue as WireValue

from app.core.types import JsonValue
from app.modules.claude.capabilities import accepts_thinking_binding
from app.modules.model_sources.forwarding import ModelSourceForwardingError

_SIGNATURE_ERROR = re.compile(r"invalid\s+[`'\" ]*signature[`'\" ]*\s+in\s+[`'\" ]*thinking[`'\" ]*\s+block", re.I)
THINKING_BINDING_BETA = "thinking-binding-controls-2026-08-01"


def _signed(block: WireValue) -> bool:
    if not isinstance(block, dict):
        return False
    kind = block.get("type")
    return (
        kind == "thinking" and bool(block.get("signature")) or kind == "redacted_thinking" and bool(block.get("data"))
    )


def bind_replayed_thinking(body: dict[str, WireValue]) -> bool:
    """Let preserved-thinking models drop prefix-mismatched blocks instead of rejecting the request.

    Anthropic validates a signed block against the system, tools, and earlier
    messages it was created with. Reconnects, model switches, and translated
    history change that prefix, so replayed blocks opt into ``drop_block``
    (CLIProxyAPI 911f49c, issue #6692). A caller-chosen behavior wins.
    """
    thinking = body.get("thinking")
    model = body.get("model")
    if not isinstance(thinking, dict) or not isinstance(model, str):
        return False
    if not accepts_thinking_binding(model, thinking.get("type")):
        return False
    binding = thinking.get("block_binding", {})
    if not isinstance(binding, dict) or "prefix_mismatch_behavior" in binding:
        return False
    messages = body.get("messages")
    contents = (
        [message.get("content") for message in messages if isinstance(message, dict)]
        if isinstance(messages, list)
        else []
    )
    if not any(_signed(block) for content in contents if isinstance(content, list) for block in content):
        return False
    body["thinking"] = {**thinking, "block_binding": {**binding, "prefix_mismatch_behavior": "drop_block"}}
    return True


def historical_recovery(
    body: dict[str, JsonValue], error: ModelSourceForwardingError, *, readable_history: bool
) -> dict[str, JsonValue] | None:
    """Retry without historical signatures; summarization keeps thinking as text."""
    detail = error.payload.get("error")
    message = detail.get("message") if isinstance(detail, dict) else None
    if error.status_code != 400 or not isinstance(message, str) or not _SIGNATURE_ERROR.search(message):
        return None
    messages = body.get("messages")
    if not isinstance(messages, list):
        return None
    # Server-tool cycles have a distinct continuation contract. Do not rewrite
    # requests containing those resources until their recovery is qualified.
    for item in messages:
        blocks = item.get("content") if isinstance(item, dict) else None
        if isinstance(blocks, list) and any(
            isinstance(block, dict)
            and (
                block.get("type") == "server_tool_use"
                or str(block.get("type", "")).endswith("_tool_result")
                and block.get("type") != "tool_result"
            )
            for block in blocks
        ):
            return None

    def has(index: int, role: str, kind: str) -> bool:
        item = messages[index]
        if not isinstance(item, dict) or item.get("role") != role:
            return False
        content = item.get("content")
        return isinstance(content, list) and any(
            isinstance(block, dict) and block.get("type") == kind for block in content
        )

    protected: set[int] = set()
    # System turns sit between a user turn and the next assistant turn; they are not part of a tool cycle.
    turns = [
        index for index, item in enumerate(messages) if not (isinstance(item, dict) and item.get("role") == "system")
    ]
    position = len(turns) - 1
    if position >= 0 and has(turns[position], "assistant", "tool_use"):
        protected.add(turns[position])
        position -= 1
    while position >= 0 and has(turns[position], "user", "tool_result"):
        position -= 1
        if position < 0 or not has(turns[position], "assistant", "tool_use"):
            return None
        protected.add(turns[position])
        position -= 1

    output: list[JsonValue] = []
    changed = False
    for index, item in enumerate(messages):
        if not isinstance(item, dict):
            return None
        content = item.get("content")
        if item.get("role") != "assistant" or not isinstance(content, list) or index in protected:
            output.append(item)
            continue
        kept: list[JsonValue] = []
        for block in content:
            kind = block.get("type") if isinstance(block, dict) else None
            if kind not in {"thinking", "redacted_thinking"}:
                kept.append(block)
                continue
            assert isinstance(block, dict)
            text = block.get("thinking")
            if readable_history and kind == "thinking" and isinstance(text, str) and text:
                kept.append({"type": "text", "text": text})
        if kept != content:
            if not kept:
                return None
            changed = True
            output.append({**item, "content": kept})
        else:
            output.append(item)
    return deepcopy({**body, "messages": output}) if changed else None
