"""Local token estimate for `count_tokens` on Responses-served models (agent-lb, opencodex)."""

from __future__ import annotations

import json

from app.core.types import JsonValue

_CHARS_PER_TOKEN = 4
_MIN_ATTACHMENT_TOKENS = 256
_ATTACHMENT_BYTES_PER_TOKEN = 512


def estimate_input_tokens(payload: dict[str, JsonValue]) -> int:
    """Characters / 4 over instructions, input and tools, with bounded attachment costs.

    Inline images and files are counted per attachment (opencodex): their base64 characters
    would otherwise overstate a screenshot by two orders of magnitude.
    """
    attachments: list[int] = []
    counted = {key: _strip_attachments(payload.get(key), attachments) for key in ("instructions", "input", "tools")}
    characters = len(json.dumps(counted, ensure_ascii=False, separators=(",", ":")))
    return max(1, -(-characters // _CHARS_PER_TOKEN) + sum(attachments))


def _strip_attachments(value: JsonValue, attachments: list[int]) -> JsonValue:
    if isinstance(value, list):
        return [_strip_attachments(item, attachments) for item in value]
    if not isinstance(value, dict):
        return value
    stripped: dict[str, JsonValue] = {}
    for key, item in value.items():
        if key in ("image_url", "file_data") and isinstance(item, str) and item.startswith("data:"):
            encoded = item.partition(",")[2]
            attachments.append(max(_MIN_ATTACHMENT_TOKENS, (len(encoded) * 3 // 4) // _ATTACHMENT_BYTES_PER_TOKEN))
            continue
        stripped[key] = _strip_attachments(item, attachments)
    return stripped
