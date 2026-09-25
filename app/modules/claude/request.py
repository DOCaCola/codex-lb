"""Project logical Messages history onto the versioned OAuth wire policy.

Always call with original history, never a previous projection. Keeping this
boundary explicit prevents compatibility prefixes becoming conversation state.
"""

from __future__ import annotations

import re
from copy import deepcopy
from dataclasses import dataclass
from typing import Literal

from pydantic import JsonValue

from app.modules.claude.credentials import ClaudeError
from app.modules.claude.profile import CLI_IDENTITY, MID_SYSTEM_BETA, RequestProfile

_MODERN = re.compile(r"^claude-(?:sonnet|opus)-5(?:-[0-9]+)?(?:-[0-9]{8})?$")
_LEGACY = re.compile(r"^claude-(?:haiku-4-5|sonnet-4-[56]|opus-4-6)(?:-[0-9]{8})?$")


@dataclass(frozen=True)
class RequestProjection:
    body: dict[str, JsonValue]
    feature_betas: tuple[str, ...]
    transformations: tuple[str, ...]


def _system_blocks(value: JsonValue) -> list[JsonValue]:
    if value is None:
        return []
    if isinstance(value, str):
        return [{"type": "text", "text": value}] if value else []
    if not isinstance(value, list):
        raise ClaudeError("Claude system instructions must be text or an array of text blocks")
    if any(
        not isinstance(block, dict) or block.get("type") != "text" or not isinstance(block.get("text"), str)
        for block in value
    ):
        raise ClaudeError("Unsupported Claude system instruction block")
    return value


def has_native_identity(body: dict[str, JsonValue]) -> bool:
    return any(
        isinstance(block, dict) and block.get("text") == CLI_IDENTITY for block in _system_blocks(body.get("system"))
    )


def project_request(
    logical: dict[str, JsonValue], profile: RequestProfile, *, endpoint: Literal["messages", "count_tokens"]
) -> RequestProjection:
    body = deepcopy(logical)
    if profile.native:
        return RequestProjection(body, (), ())
    blocks = _system_blocks(body.pop("system", None))
    messages = body.get("messages")
    if not isinstance(messages, list) or not messages:
        raise ClaudeError("Claude requests require a nonempty messages array")
    if any(not isinstance(message, dict) for message in messages):
        raise ClaudeError("Invalid Claude message")
    if endpoint == "messages":
        body["system"] = [{"type": "text", "text": CLI_IDENTITY}]
    if not blocks:
        return RequestProjection(body, (), ("oauth_identity",) if endpoint == "messages" else ())

    model = body.get("model")
    if not isinstance(model, str):
        raise ClaudeError("Claude model is required")
    modern = bool(_MODERN.fullmatch(model))
    if not modern and not _LEGACY.fullmatch(model):
        raise ClaudeError("OAuth instruction placement is not qualified for this Claude model")

    # Server tool artifacts may bind the entire layout, not merely their own
    # signature bytes. Ordinary client tools named 'advisor' are not artifacts.
    for message in messages:
        assert isinstance(message, dict)
        content = message.get("content")
        if isinstance(content, list) and any(
            isinstance(block, dict)
            and (
                block.get("type") == "server_tool_use"
                or str(block.get("type", "")).endswith("_tool_result")
                and block.get("type") != "tool_result"
            )
            for block in content
        ):
            raise ClaudeError("OAuth instruction relocation cannot alter server-tool history")

    if modern:
        # Insert only after an ordinary user turn, never between an assistant
        # tool call and its result. No existing message/block is rewritten.
        index = next(
            (
                index
                for index, message in enumerate(messages)
                if isinstance(message, dict)
                and message.get("role") == "user"
                and not (
                    isinstance(message.get("content"), list)
                    and any(
                        isinstance(block, dict) and block.get("type") == "tool_result" for block in message["content"]
                    )
                )
            ),
            None,
        )
        if index is None:
            raise ClaudeError("OAuth instructions need an ordinary user turn before tool continuation")
        messages.insert(index + 1, {"role": "system", "content": blocks})
        return RequestProjection(body, (MID_SYSTEM_BETA,), ("oauth_identity", "mid_system_instructions"))

    # Separate delimiter blocks preserve caller text and cache breakpoints
    # exactly. This intentionally lowers role authority, unlike modern system
    # turns; the selected transformation is explicit to diagnostics/tests.
    messages.insert(
        0,
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "<system-reminder>"},
                *blocks,
                {"type": "text", "text": "</system-reminder>"},
            ],
        },
    )
    return RequestProjection(body, (), ("oauth_identity", "user_reminder_instructions"))
