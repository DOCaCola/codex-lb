"""Signed thinking signatures that carry Responses reasoning through Claude Code.

Claude Code replays a thinking block's signature verbatim. The signature holds the upstream
encrypted reasoning, its item ID and the routed model, authenticated with an installation
key, so it replays only to the model that produced it, whether selected by name or by
alias (opencodex `ocxr1`).
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
from dataclasses import dataclass

from app.core.crypto import get_or_create_key
from app.core.messages.errors import MessagesRequestError
from app.core.types import JsonValue

PROXY_SIGNATURE_PREFIX = "clb1:"
_VERSION = 1
_KEY_PURPOSE = b"codex-lb messages reasoning envelope v1"


@dataclass(frozen=True, slots=True)
class ReasoningEnvelope:
    model: str
    item_id: str
    encrypted_content: str


def envelope_key() -> bytes:
    return hmac.new(get_or_create_key(), _KEY_PURPOSE, hashlib.sha256).digest()


def seal_reasoning(envelope: ReasoningEnvelope, key: bytes) -> str:
    body = {
        "v": _VERSION,
        "model": envelope.model,
        "id": envelope.item_id,
        "enc": envelope.encrypted_content,
        "tag": _tag(envelope, key),
    }
    encoded = base64.urlsafe_b64encode(json.dumps(body, separators=(",", ":")).encode()).decode().rstrip("=")
    return PROXY_SIGNATURE_PREFIX + encoded


def is_proxy_signature(signature: object) -> bool:
    return isinstance(signature, str) and signature.startswith(PROXY_SIGNATURE_PREFIX)


def strip_proxy_thinking(body: dict[str, JsonValue]) -> None:
    """Remove proxy-signed thinking before a Messages request reaches Anthropic.

    A Claude Code session can switch from a Responses-served model to Claude; Anthropic cannot
    verify these signatures (opencodex `nativeAnthropicProjection`). An assistant message left
    without content is removed.
    """
    messages = body.get("messages")
    if not isinstance(messages, list):
        return
    kept: list[JsonValue] = []
    changed = False
    for message in messages:
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(message, dict) or message.get("role") != "assistant" or not isinstance(content, list):
            kept.append(message)
            continue
        retained = [
            block
            for block in content
            if not (
                isinstance(block, dict)
                and block.get("type") == "thinking"
                and is_proxy_signature(block.get("signature"))
            )
        ]
        if len(retained) == len(content):
            kept.append(message)
            continue
        changed = True
        if retained:
            kept.append({**message, "content": retained})
    if changed:
        body["messages"] = kept


def open_reasoning(signature: str, key: bytes) -> ReasoningEnvelope:
    """Verify a proxy signature; a malformed or forged envelope is a client error."""
    encoded = signature.removeprefix(PROXY_SIGNATURE_PREFIX)
    try:
        body = json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))
    except (binascii.Error, UnicodeDecodeError, ValueError) as exc:
        raise MessagesRequestError("Thinking block signature is not a valid reasoning envelope") from exc
    if (
        not isinstance(body, dict)
        or body.get("v") != _VERSION
        or not all(isinstance(body.get(field), str) for field in ("model", "id", "enc", "tag"))
    ):
        raise MessagesRequestError("Thinking block signature is not a valid reasoning envelope")
    envelope = ReasoningEnvelope(model=body["model"], item_id=body["id"], encrypted_content=body["enc"])
    if not hmac.compare_digest(body["tag"], _tag(envelope, key)):
        raise MessagesRequestError("Thinking block signature failed verification")
    return envelope


def _tag(envelope: ReasoningEnvelope, key: bytes) -> str:
    message = json.dumps([envelope.model, envelope.item_id, envelope.encrypted_content], separators=(",", ":"))
    return hmac.new(key, message.encode(), hashlib.sha256).hexdigest()
