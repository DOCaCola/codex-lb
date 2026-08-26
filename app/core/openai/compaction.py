from __future__ import annotations

import base64
from binascii import Error as Base64Error

from app.core.types import JsonValue
from app.core.utils.json_guards import is_json_list, is_json_mapping

CODEX_LB_COMPACTION_PREFIX = "clb1:"
COMPACTION_SUMMARY_PREFIX = (
    "Another language model started to solve this problem and produced a summary of its thinking process. "
    "You also have access to the state of the tools that were used by that language model. Use this to build "
    "on the work that has already been done and avoid duplicating work. Here is the summary produced by the "
    "other language model, use the information in this summary to assist with your own analysis:"
)
COMPACTION_UNAVAILABLE_NOTE = (
    "[earlier conversation was compacted; the summary is stored in a format this model cannot read]"
)
COMPACTION_PROMPT = (
    "You are performing a CONTEXT CHECKPOINT COMPACTION. Create a handoff summary for another LLM that will "
    "resume the task.\n\n"
    "Include:\n"
    "- Current progress and key decisions made\n"
    "- Important context, constraints, or user preferences\n"
    "- What remains to be done (clear next steps)\n"
    "- Any critical data, examples, or references needed to continue\n\n"
    "Be concise, structured, and focused on helping the next LLM seamlessly continue the work."
)

_COMPACTION_ITEM_TYPES = frozenset({"compaction", "compaction_summary", "context_compaction"})

type MutableJsonObject = dict[str, JsonValue]


def encode_codex_lb_compaction_summary(summary: str) -> str:
    encoded = base64.b64encode(summary.encode("utf-8")).decode("ascii")
    return f"{CODEX_LB_COMPACTION_PREFIX}{encoded}"


def decode_codex_lb_compaction_summary(encrypted_content: str) -> str | None:
    if not encrypted_content.startswith(CODEX_LB_COMPACTION_PREFIX):
        return None
    encoded = encrypted_content[len(CODEX_LB_COMPACTION_PREFIX) :]
    if not encoded:
        return None
    try:
        decoded = base64.b64decode(encoded, validate=True).decode("utf-8")
    except (Base64Error, UnicodeDecodeError, ValueError):
        return None
    return decoded if decoded.strip() else None


def lower_codex_lb_compaction_items(payload: MutableJsonObject) -> None:
    """Replace proxy-owned replay items with explicit summary messages."""

    input_value = payload.get("input")
    if not is_json_list(input_value):
        return
    changed = False
    lowered: list[JsonValue] = []
    for item in input_value:
        if not is_json_mapping(item) or item.get("type") not in _COMPACTION_ITEM_TYPES:
            lowered.append(item)
            continue
        encrypted_content = item.get("encrypted_content")
        if not isinstance(encrypted_content, str) or not encrypted_content.startswith(CODEX_LB_COMPACTION_PREFIX):
            lowered.append(item)
            continue
        summary = decode_codex_lb_compaction_summary(encrypted_content)
        lowered.append(
            _summary_message(summary) if summary is not None else _summary_message(COMPACTION_UNAVAILABLE_NOTE)
        )
        changed = True
    if changed:
        payload["input"] = lowered


def lower_opaque_compaction_items_for_model_source(payload: MutableJsonObject) -> None:
    """Prevent native opaque compaction state from reaching a routed source."""

    input_value = payload.get("input")
    if not is_json_list(input_value):
        return
    changed = False
    lowered: list[JsonValue] = []
    for item in input_value:
        if not is_json_mapping(item) or item.get("type") not in _COMPACTION_ITEM_TYPES:
            lowered.append(item)
            continue
        encrypted_content = item.get("encrypted_content")
        if not isinstance(encrypted_content, str):
            lowered.append(item)
            continue
        lowered.append(_summary_message(COMPACTION_UNAVAILABLE_NOTE))
        changed = True
    if changed:
        payload["input"] = lowered


def _summary_message(summary: str) -> dict[str, JsonValue]:
    text = summary if summary == COMPACTION_UNAVAILABLE_NOTE else f"{COMPACTION_SUMMARY_PREFIX}\n\n{summary}"
    return {
        "type": "message",
        "role": "user",
        "content": [{"type": "input_text", "text": text}],
    }
