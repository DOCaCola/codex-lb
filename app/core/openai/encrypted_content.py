"""Recovery from upstream rejections of replayed encrypted content.

Codex keeps upstream-minted ciphertext in its local history and resends it on
every later turn: ``encrypted_content`` of reasoning and compaction items, and
``encrypted_content`` parts of tool outputs and subagent messages. When upstream
explicitly refuses such ciphertext, every later turn of that conversation would
fail the same way. The proxy remembers the SHA-256 digests of the ciphertext a
rejected request carried and removes exactly those values from later native
requests. Ciphertext minted afterwards has other digests and passes unchanged.

Only explicit upstream identities qualify; a generic ``server_error`` never
does. Checkpoint handoff requests are excluded: their only payload is the
checkpoint, and a handoff never retries with a placeholder.

Every entry point takes the request's operation explicitly. Upstream readers of
the WebSocket and HTTP bridge surfaces run outside the request task, so they
pass the operation their request state captured at creation.
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from collections import OrderedDict
from collections.abc import Callable, Iterator, Mapping, Sequence

from app.core.types import JsonValue
from app.core.usage.request_operation import RequestOperation
from app.core.utils.json_guards import is_json_list, is_json_mapping

logger = logging.getLogger(__name__)

ENCRYPTED_CONTENT_REJECTION_CODE = "invalid_encrypted_content"
ENCRYPTED_FUNCTION_OUTPUT_REJECTION = "Encrypted function output content could not be decrypted or decoded."
REJECTED_COMPACTION_NOTE = (
    "[Earlier conversation was compacted, but its stored summary could not be read and is unavailable.]"
)
OMITTED_ENCRYPTED_PART_TEXT = "[encrypted content omitted]"

RETENTION_SECONDS = 24 * 3600
MAX_DIGESTS = 20_000

_COMPACTION_ITEM_TYPES = frozenset({"compaction", "compaction_summary"})
_PART_CARRYING_FIELDS = {
    "function_call_output": "output",
    "custom_tool_call_output": "output",
    "agent_message": "content",
}


def is_encrypted_content_rejection(code: str | None, message: str | None) -> bool:
    """Return whether upstream explicitly refused replayed ciphertext."""
    if code == ENCRYPTED_CONTENT_REJECTION_CODE:
        return True
    text = message or ""
    if text == ENCRYPTED_FUNCTION_OUTPUT_REJECTION:
        return True
    if text.startswith("The encrypted content for item ") and "could not be verified" in text:
        return True
    return "was not issued to this caller" in text and ("encrypted_content" in text or "reasoning" in text)


def encrypted_content_recovery_applies(operation: RequestOperation) -> bool:
    return operation is not RequestOperation.CHECKPOINT_HANDOFF


def _digest(ciphertext: str) -> str:
    return hashlib.sha256(ciphertext.encode()).hexdigest()


def _encrypted_part_text(part: JsonValue) -> str | None:
    if not is_json_mapping(part) or part.get("type") != "encrypted_content":
        return None
    ciphertext = part.get("encrypted_content")
    return ciphertext if isinstance(ciphertext, str) and ciphertext else None


def _item_ciphertexts(item: JsonValue) -> Iterator[str]:
    if not is_json_mapping(item):
        return
    item_type = item.get("type")
    if item_type == "reasoning" or item_type in _COMPACTION_ITEM_TYPES:
        ciphertext = item.get("encrypted_content")
        if isinstance(ciphertext, str) and ciphertext:
            yield ciphertext
        return
    field = _PART_CARRYING_FIELDS.get(item_type) if isinstance(item_type, str) else None
    parts = item.get(field) if field is not None else None
    if is_json_list(parts):
        for part in parts:
            ciphertext = _encrypted_part_text(part)
            if ciphertext is not None:
                yield ciphertext


class RejectedEncryptedContent:
    """Digests of ciphertext upstream refused, kept while conversations still replay it."""

    def __init__(
        self,
        *,
        retention_seconds: float = RETENTION_SECONDS,
        max_digests: int = MAX_DIGESTS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._retention_seconds = retention_seconds
        self._max_digests = max_digests
        self._clock = clock
        self._expires_at: OrderedDict[str, float] = OrderedDict()
        self._lock = threading.Lock()

    def remember(self, input_items: Sequence[JsonValue]) -> int:
        """Record the ciphertext of a rejected request; return how many digests are new."""
        digests = {_digest(ciphertext) for item in input_items for ciphertext in _item_ciphertexts(item)}
        if not digests:
            return 0
        now = self._clock()
        expires_at = now + self._retention_seconds
        added = 0
        with self._lock:
            for digest in digests:
                previous = self._expires_at.pop(digest, None)
                if previous is None or previous <= now:
                    added += 1
                self._expires_at[digest] = expires_at
            while len(self._expires_at) > self._max_digests:
                self._expires_at.popitem(last=False)
        return added

    def strip(self, input_items: Sequence[JsonValue]) -> tuple[list[JsonValue], int] | None:
        """Remove remembered ciphertext; ``None`` when the input carries none of it."""
        with self._lock:
            if not self._expires_at:
                return None
        stripped_items: list[JsonValue] = []
        stripped = 0
        for item in input_items:
            replacement, removed = self._strip_item(item)
            stripped += removed
            if replacement is not None:
                stripped_items.append(replacement)
        return (stripped_items, stripped) if stripped else None

    def clear(self) -> None:
        with self._lock:
            self._expires_at.clear()

    def _is_rejected(self, ciphertext: str) -> bool:
        digest = _digest(ciphertext)
        now = self._clock()
        with self._lock:
            expires_at = self._expires_at.get(digest)
            if expires_at is None:
                return False
            if expires_at <= now:
                del self._expires_at[digest]
                return False
            self._expires_at[digest] = now + self._retention_seconds
            self._expires_at.move_to_end(digest)
            return True

    def _strip_item(self, item: JsonValue) -> tuple[JsonValue | None, int]:
        if not is_json_mapping(item):
            return item, 0
        item_type = item.get("type")
        if item_type == "reasoning" or item_type in _COMPACTION_ITEM_TYPES:
            ciphertext = item.get("encrypted_content")
            if not isinstance(ciphertext, str) or not ciphertext or not self._is_rejected(ciphertext):
                return item, 0
            if item_type == "reasoning":
                # Native requests are stateless; reasoning without its ciphertext
                # is not replayable state, so the whole item goes.
                return None, 1
            return {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": REJECTED_COMPACTION_NOTE}],
            }, 1
        field = _PART_CARRYING_FIELDS.get(item_type) if isinstance(item_type, str) else None
        parts = item.get(field) if field is not None else None
        if field is None or not is_json_list(parts):
            return item, 0
        removed = 0
        replaced_parts: list[JsonValue] = []
        for part in parts:
            ciphertext = _encrypted_part_text(part)
            if ciphertext is not None and self._is_rejected(ciphertext):
                removed += 1
                replaced_parts.append({"type": "input_text", "text": OMITTED_ENCRYPTED_PART_TEXT})
            else:
                replaced_parts.append(part)
        if not removed:
            return item, 0
        return {**item, field: replaced_parts}, removed


REJECTED_ENCRYPTED_CONTENT = RejectedEncryptedContent()


def remember_rejected_encrypted_content(input_value: JsonValue | None, operation: RequestOperation) -> int:
    """Remember the ciphertext of a request upstream rejected; return the new digest count."""
    if not encrypted_content_recovery_applies(operation) or not is_json_list(input_value):
        return 0
    return REJECTED_ENCRYPTED_CONTENT.remember(input_value)


def strip_rejected_encrypted_content(
    payload: Mapping[str, JsonValue], operation: RequestOperation
) -> Mapping[str, JsonValue]:
    """Return ``payload`` without ciphertext upstream has already refused."""
    input_value = payload.get("input")
    if not encrypted_content_recovery_applies(operation) or not is_json_list(input_value):
        return payload
    result = REJECTED_ENCRYPTED_CONTENT.strip(input_value)
    if result is None:
        return payload
    stripped_items, stripped = result
    logger.info("rejected_encrypted_content_stripped items=%d", stripped)
    return {**payload, "input": stripped_items}


def _request_text_payload(request_text: str | None) -> dict[str, JsonValue] | None:
    if not request_text:
        return None
    try:
        payload = json.loads(request_text)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def remember_rejected_encrypted_content_text(request_text: str | None, operation: RequestOperation) -> int:
    """Remember the ciphertext of a rejected serialized ``response.create`` body."""
    payload = _request_text_payload(request_text)
    return remember_rejected_encrypted_content(payload.get("input"), operation) if payload is not None else 0


def strip_rejected_encrypted_content_text(request_text: str | None, operation: RequestOperation) -> str | None:
    """Return the serialized body without refused ciphertext, or ``None`` when unchanged."""
    payload = _request_text_payload(request_text)
    if payload is None:
        return None
    stripped = strip_rejected_encrypted_content(payload, operation)
    if stripped is payload:
        return None
    return json.dumps(stripped, ensure_ascii=True, separators=(",", ":"))
