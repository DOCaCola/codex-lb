"""Structured Claude session metadata; never reinterpret an opaque user ID."""

from __future__ import annotations

import json
from collections.abc import Mapping
from uuid import UUID

from pydantic import JsonValue, TypeAdapter

from app.modules.claude.credentials import ClaudeError
from app.modules.claude.profile import RequestProfile, session_identity

_JSON_OBJECT = TypeAdapter(dict[str, JsonValue])


def session_metadata(body: dict[str, JsonValue]) -> dict[str, JsonValue] | None:
    metadata = body.get("metadata")
    if metadata is None:
        return None
    if not isinstance(metadata, dict):
        raise ClaudeError("Claude metadata must be an object")
    if "user_id" not in metadata:
        return None
    raw = metadata["user_id"]
    if not isinstance(raw, str):
        raise ClaudeError("Claude OAuth user_id must be structured session metadata")
    try:
        identity = _JSON_OBJECT.validate_json(raw)
        for field in ("session_id", "parent_session_id"):
            if field == "parent_session_id" and field not in identity:
                continue
            value = identity.get(field)
            if not isinstance(value, str):
                raise ValueError
            UUID(value)
        if not isinstance(identity.get("device_id"), str) or not identity["device_id"]:
            raise ValueError
    except ValueError as exc:
        raise ClaudeError("Claude OAuth user_id must contain valid structured session metadata") from exc
    return identity


def project_session(body: dict[str, JsonValue], profile: RequestProfile, *, source_id: str, client_scope: str) -> bool:
    identity = session_metadata(body)
    if identity is None:
        return False
    identity["session_id"] = profile.session_id
    parent = identity.get("parent_session_id")
    if isinstance(parent, str):
        identity["parent_session_id"] = session_identity(source_id, client_scope, parent)
    metadata = body["metadata"]
    assert isinstance(metadata, dict)
    metadata["user_id"] = json.dumps(identity, separators=(",", ":"))
    return True


def has_helper_identity(body: dict[str, JsonValue], headers: Mapping[str, str], *, count_tokens: bool) -> bool:
    """Recognize bounded helper shapes, not arbitrary Messages with a CLI UA."""
    if count_tokens:
        return True  # The caller still checks all CLI software/OAuth signals.
    identity = session_metadata(body)
    values = {key.lower(): value for key, value in headers.items()}
    if identity is None or values.get("x-claude-code-session-id") != identity["session_id"]:
        return False
    model = body.get("model")
    if not isinstance(model, str) or model.removeprefix("anthropic/") != "claude-haiku-4-5-20251001":
        return False
    messages = body.get("messages")
    if not isinstance(messages, list) or len(messages) != 1:
        return False
    message = messages[0]
    if not isinstance(message, dict) or message.get("role") != "user":
        return False
    if set(body) == {"model", "max_tokens", "messages", "metadata"}:
        return body["max_tokens"] == 1 and isinstance(message.get("content"), str)
    output = body.get("output_config")
    if set(body) != {
        "model",
        "messages",
        "system",
        "tools",
        "metadata",
        "max_tokens",
        "thinking",
        "temperature",
        "output_config",
        "stream",
    }:
        return False
    content = message.get("content")
    if not isinstance(content, list) or len(content) != 1:
        return False
    block = content[0]
    if not isinstance(block, dict) or set(block) != {"type", "text"} or block["type"] != "text":
        return False
    if not isinstance(block["text"], str):
        return False
    title_format = {
        "type": "json_schema",
        "schema": {
            "type": "object",
            "properties": {"title": {"type": "string"}},
            "required": ["title"],
            "additionalProperties": False,
        },
    }
    return (
        body.get("thinking") == {"type": "disabled"}
        and body.get("tools") == []
        and body.get("stream") is True
        and body.get("max_tokens") == 32000
        and body.get("temperature") == 1
        and output == {"format": title_format}
    )
