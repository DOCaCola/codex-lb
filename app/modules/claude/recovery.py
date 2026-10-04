"""One-shot, pre-delivery recovery for rejected historical thinking."""

from __future__ import annotations

import re
from copy import deepcopy

from app.core.types import JsonValue
from app.modules.model_sources.forwarding import ModelSourceForwardingError

_SIGNATURE_ERROR = re.compile(r"invalid\s+[`'\" ]*signature[`'\" ]*\s+in\s+[`'\" ]*thinking[`'\" ]*\s+block", re.I)


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
