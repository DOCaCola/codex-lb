"""Portable reasoning and item identities at the native Responses boundary."""

import logging
from collections.abc import Mapping

from app.core.openai.exceptions import ClientPayloadError
from app.core.types import JsonValue
from app.core.utils.json_guards import is_json_list, is_json_mapping

logger = logging.getLogger(__name__)

CLAUDE_REASONING_PREFIX = "claude-v1."

_ITEM_ID_PREFIXES = {
    "message": "msg_",
    "agent_message": "amsg_",
    "reasoning": "rs_",
    "function_call": "fc_",
    "custom_tool_call": "ctc_",
    "tool_search_call": "tsc_",
    "web_search_call": "ws_",
}


def ensure_native_provider_history(payload: Mapping[str, JsonValue]) -> None:
    """Unscoped low-level callers cannot authenticate or drop Claude state."""
    items = payload.get("input")
    if not is_json_list(items):
        return
    for index, item in enumerate(items):
        token = item.get("encrypted_content") if is_json_mapping(item) else None
        if isinstance(token, str) and token.startswith(CLAUDE_REASONING_PREFIX):
            raise ClientPayloadError(
                "Claude history requires authenticated projection before native OpenAI dispatch.",
                param=f"input[{index}]",
                code="nonportable_provider_history",
            )


def sanitize_native_reasoning_input(payload: Mapping[str, JsonValue]) -> dict[str, JsonValue]:
    """Forward reasoning only as OpenAI's own encrypted state.

    Native requests are stateless (`store=false`), so a reasoning item without `encrypted_content`
    is not a lookup reference. OpenAI accepts such summary-only reasoning as fresh input but refuses
    to chain a later turn onto a response that stored it as unverifiable hidden reasoning.
    """
    sanitized = dict(payload)
    items = sanitized.get("input")
    if not is_json_list(items):
        return sanitized
    normalized: list[JsonValue] = []
    omitted = 0
    for item in items:
        if not is_json_mapping(item) or item.get("type") != "reasoning":
            normalized.append(item)
            continue
        encrypted = item.get("encrypted_content")
        if not isinstance(encrypted, str) or not encrypted:
            omitted += 1
            continue
        result = dict(item)
        content = result.get("content")
        if is_json_list(content) and content:
            result["content"] = []
        result.setdefault("summary", [])
        result.pop("status", None)
        normalized.append(result)
    if omitted:
        logger.info("native_reasoning_projection unverifiable_omitted=%d", omitted)
    sanitized["input"] = normalized
    return sanitized


def strip_invalid_native_item_ids(payload: Mapping[str, JsonValue]) -> dict[str, JsonValue]:
    """Foreign identities are not renamed into fictitious OpenAI store items."""
    sanitized = dict(payload)
    items = sanitized.get("input")
    if not is_json_list(items):
        return sanitized
    normalized: list[JsonValue] = []
    for item in items:
        if not is_json_mapping(item):
            normalized.append(item)
            continue
        kind = item.get("type", "message" if "role" in item else None)
        prefix = _ITEM_ID_PREFIXES.get(kind) if isinstance(kind, str) else None
        identity = item.get("id")
        if prefix is None or "id" not in item or (isinstance(identity, str) and identity.startswith(prefix)):
            normalized.append(item)
            continue
        result = dict(item)
        result.pop("id")
        normalized.append(result)
    sanitized["input"] = normalized
    return sanitized
