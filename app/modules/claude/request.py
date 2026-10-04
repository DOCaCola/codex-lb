"""Project logical Messages history onto the versioned OAuth wire policy.

Always call with original history, never a previous projection. Keeping this
boundary explicit prevents compatibility prefixes becoming conversation state.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, replace
from typing import Literal

from pydantic import JsonValue

from app.modules.claude.capabilities import model_policy
from app.modules.claude.credentials import ClaudeError
from app.modules.claude.profile import CLI_IDENTITY, MID_SYSTEM_BETA, RequestProfile


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
    blocks = _system_blocks(body.get("system"))
    # Claude Code's volatile billing marker must stay first: moving it into
    # the ordinary cached prefix changes every subsequent cache key. Identity
    # recognition still requires the software/OAuth signals in recognize_native.
    billing_first = bool(
        blocks
        and isinstance(blocks[0], dict)
        and isinstance(blocks[0].get("text"), str)
        and blocks[0]["text"].startswith("x-anthropic-billing-header:")
    )
    return billing_first or any(isinstance(block, dict) and block.get("text") == CLI_IDENTITY for block in blocks)


def project_request(
    logical: dict[str, JsonValue],
    profile: RequestProfile,
    *,
    endpoint: Literal["messages", "count_tokens"],
    translated: bool = False,
) -> RequestProjection:
    projection = _project_request(logical, profile, endpoint=endpoint, translated=translated)
    if not profile.native and _preserve_cache_ttl_order(logical, projection.body):
        return replace(projection, transformations=(*projection.transformations, "cache_ttl_order"))
    return projection


def _cache_controls(body: dict[str, JsonValue]) -> list[dict[str, JsonValue]]:
    """Visit cache policy locations only, never opaque tool payloads."""
    blocks: list[JsonValue] = []
    for key in ("tools", "system"):
        value = body.get(key)
        if isinstance(value, list):
            blocks.extend(value)
    messages = body.get("messages")
    if isinstance(messages, list):
        for message in messages:
            content = message.get("content") if isinstance(message, dict) else None
            if isinstance(content, list):
                blocks.extend(content)
    controls = [block.get("cache_control") for block in blocks if isinstance(block, dict)]
    controls.append(body.get("cache_control"))
    return [control for control in controls if isinstance(control, dict)]


def _preserve_cache_ttl_order(logical: dict[str, JsonValue], body: dict[str, JsonValue]) -> bool:
    original = _cache_controls(logical)
    projected = _cache_controls(body)
    # Invalid caller policy belongs to upstream validation, not normalization.
    if any(control.get("type") != "ephemeral" or control.get("ttl", "5m") not in ("5m", "1h") for control in original):
        return False
    seen_short = False
    for control in original:
        if control.get("ttl", "5m") == "5m":
            seen_short = True
        elif seen_short:
            return False
    changed = False
    later_long = False
    for control in reversed(projected):
        if control.get("ttl") == "1h":
            later_long = True
        elif later_long:
            control["ttl"] = "1h"
            changed = True
    return changed


def _project_request(
    logical: dict[str, JsonValue],
    profile: RequestProfile,
    *,
    endpoint: Literal["messages", "count_tokens"],
    translated: bool = False,
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
    # Conversation-positioned system turns (translated developer messages) need the same beta.
    system_turns = (MID_SYSTEM_BETA,) if any(message.get("role") == "system" for message in messages) else ()
    if not blocks:
        return RequestProjection(body, system_turns, ("oauth_identity",) if endpoint == "messages" else ())

    model = body.get("model")
    if not isinstance(model, str):
        raise ClaudeError("Claude model is required")
    policy = model_policy(model)
    if policy is None:
        raise ClaudeError("OAuth instruction placement is not qualified for this Claude model")
    modern = policy.mid_system

    # Server tool artifacts may bind the entire layout, not merely their own
    # signature bytes. Ordinary client tools named 'advisor' are not artifacts.
    for message in messages:
        assert isinstance(message, dict)
        content = message.get("content")
        if (
            not translated
            and isinstance(content, list)
            and any(
                isinstance(block, dict)
                and (
                    block.get("type") == "server_tool_use"
                    or str(block.get("type", "")).endswith("_tool_result")
                    and block.get("type") != "tool_result"
                )
                for block in content
            )
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
    return RequestProjection(body, system_turns, ("oauth_identity", "user_reminder_instructions"))
