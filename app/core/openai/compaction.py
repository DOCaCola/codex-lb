from __future__ import annotations

import base64
import logging
from binascii import Error as Base64Error
from collections.abc import Mapping

from app.core.openai.exceptions import ClientPayloadError
from app.core.types import JsonValue
from app.core.utils.json_guards import is_json_list, is_json_mapping
from app.core.utils.request_id import get_request_id

logger = logging.getLogger(__name__)

CODEX_LB_COMPACTION_PREFIX = "clb1:"
COMPACTION_SUMMARY_PREFIX = (
    "Another language model started to solve this problem and produced a summary of its thinking process. "
    "You also have access to the state of the tools that were used by that language model. Use this to build "
    "on the work that has already been done and avoid duplicating work. Here is the summary produced by the "
    "other language model, use the information in this summary to assist with your own analysis:"
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
_LOCAL_MARKER_KEYS = frozenset({"type", "id", "encrypted_content", "internal_chat_message_metadata_passthrough"})

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
    for index, item in enumerate(input_value):
        if not is_json_mapping(item) or item.get("type") not in _COMPACTION_ITEM_TYPES:
            lowered.append(item)
            continue
        summary = _proxy_compaction_summary(item, index)
        if summary is None:
            lowered.append(item)
            continue
        lowered.append(_summary_message(summary))
        changed = True
    if changed:
        payload["input"] = lowered


def lower_opaque_compaction_items_for_model_source(payload: MutableJsonObject) -> None:
    """Prevent native opaque compaction state from reaching a routed source."""

    input_value = payload.get("input")
    if not is_json_list(input_value):
        return
    lowered: list[JsonValue] = []
    omitted = 0
    changed = False
    for index, item in enumerate(input_value):
        if not is_json_mapping(item) or item.get("type") not in _COMPACTION_ITEM_TYPES:
            lowered.append(item)
            continue
        projected = project_source_compaction_item(item, index)
        if projected is None:
            omitted += 1
        else:
            lowered.append(projected)
            changed = True
    if omitted or changed:
        payload["input"] = lowered
    if omitted:
        logger.info("source_compaction_markers_skipped request_id=%s count=%d", get_request_id(), omitted)


def project_source_compaction_item(item: Mapping[str, JsonValue], index: int) -> MutableJsonObject | None:
    """Validate one checkpoint using its original logical-input position."""
    encrypted = item.get("encrypted_content")
    unsupported_marker = item.get("type") == "context_compaction" and not item.keys() <= _LOCAL_MARKER_KEYS
    if not unsupported_marker:
        summary = _proxy_compaction_summary(item, index)
        if summary is not None:
            return _summary_message(summary)
    if item.get("type") == "context_compaction" and encrypted is None and not unsupported_marker:
        # Local summaries are independent ordinary messages, not in this marker.
        return None
    reason = "opaque_checkpoint"
    if unsupported_marker:
        reason = "unsupported_marker_payload"
    elif encrypted is not None and (not isinstance(encrypted, str) or not encrypted):
        reason = "invalid_ciphertext"
    elif encrypted is None:
        reason = "missing_checkpoint_payload"
    raise _checkpoint_error(
        item,
        index,
        reason=reason,
        message="This model source cannot read the compaction checkpoint; use the original provider or resend "
        "the complete materialized history.",
    )


def _proxy_compaction_summary(item: Mapping[str, JsonValue], index: int) -> str | None:
    encrypted_content = item.get("encrypted_content")
    if not isinstance(encrypted_content, str) or not encrypted_content.startswith(CODEX_LB_COMPACTION_PREFIX):
        return None
    summary = decode_codex_lb_compaction_summary(encrypted_content)
    if summary is None:
        raise _checkpoint_error(
            item,
            index,
            reason="corrupt_proxy_checkpoint",
            message="The proxy compaction checkpoint is corrupt; resend the complete history or a valid checkpoint.",
        )
    return summary


def _checkpoint_error(item: Mapping[str, JsonValue], index: int, *, reason: str, message: str) -> ClientPayloadError:
    logger.warning(
        "compaction_checkpoint_rejected request_id=%s input_index=%d item_type=%s ciphertext_present=%s reason=%s",
        get_request_id(),
        index,
        item["type"],
        item.get("encrypted_content") is not None,
        reason,
    )
    return ClientPayloadError(message, param=f"input[{index}]", code="compaction_history_unavailable")


def _summary_message(summary: str) -> dict[str, JsonValue]:
    text = f"{COMPACTION_SUMMARY_PREFIX}\n\n{summary}"
    return {
        "type": "message",
        "role": "user",
        "content": [{"type": "input_text", "text": text}],
    }
