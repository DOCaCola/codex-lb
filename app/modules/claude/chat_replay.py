"""Claude-only Chat history: canonical matching and content-preserving projection."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import cast

from app.core.openai.chat_requests import _sanitize_user_messages
from app.core.openai.contracts import OpenAIMessage
from app.core.openai.exceptions import ClientPayloadError
from app.core.openai.message_coercion import coerce_messages
from app.core.types import JsonValue
from app.modules.claude.opaque import ClaudeOpaqueState
from app.modules.proxy.replay_store import HTTPFallbackReplayStore, ReplayHistory, ReplayScope

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ChatToolCall:
    call_id: str
    name: str
    arguments: str


@dataclass(frozen=True)
class ChatToolCycle:
    start: int
    assistant_end: int
    end: int
    calls: tuple[ChatToolCall, ...]
    reasoning: str | None


@dataclass(frozen=True)
class ChatHistory:
    """Canonical visible items omit reasoning until the replay decision is made."""

    items: list[JsonValue]
    cycles: tuple[ChatToolCycle, ...]
    reasoning_at: dict[int, str]

    @classmethod
    def from_messages(cls, messages: list[OpenAIMessage]) -> ChatHistory:
        items: list[JsonValue] = []
        cycles: list[ChatToolCycle] = []
        reasoning_at: dict[int, str] = {}
        pending: tuple[int, int, tuple[ChatToolCall, ...], str | None] | None = None
        remaining: set[str] = set()
        seen_calls: set[str] = set()
        for index, message in enumerate(_sanitize_user_messages(messages)):
            role = message.get("role")
            if role in ("system", "developer"):
                if pending is not None:
                    raise ClientPayloadError(
                        "Tool results are required before another message", param=f"messages[{index}]"
                    )
                continue
            if role == "tool":
                if pending is None:
                    raise ClientPayloadError("No matching Claude tool call for this result", param=f"messages[{index}]")
                call_id = _tool_call_id(message, index)
                if call_id not in remaining:
                    raise ClientPayloadError("Duplicate or unmatched Claude tool result", param=f"messages[{index}]")
                items.append(
                    {"type": "function_call_output", "call_id": call_id, "output": _tool_output(message, index)}
                )
                remaining.remove(call_id)
                if not remaining:
                    start, assistant_end, calls, reasoning = pending
                    cycles.append(ChatToolCycle(start, assistant_end, len(items), calls, reasoning))
                    pending = None
                continue
            if pending is not None:
                raise ClientPayloadError("Tool results are required before another message", param=f"messages[{index}]")
            _, converted = coerce_messages("", [cast(JsonValue, message)])
            start = len(items)
            items.extend(converted)
            if role != "assistant":
                continue
            raw_reasoning = message.get("reasoning_content")
            if raw_reasoning is not None and not isinstance(raw_reasoning, str):
                raise ClientPayloadError(
                    "reasoning_content must be text or null", param=f"messages[{index}].reasoning_content"
                )
            reasoning = raw_reasoning if isinstance(raw_reasoning, str) and raw_reasoning else None
            calls = tuple(
                _call_from_item(item, index)
                for item in converted
                if isinstance(item, dict) and item.get("type") == "function_call"
            )
            if not calls:
                if reasoning is not None:
                    reasoning_at[start] = reasoning
                continue
            call_ids = {call.call_id for call in calls}
            if len(call_ids) != len(calls) or call_ids & seen_calls:
                raise ClientPayloadError("Duplicate Claude tool call ID", param=f"messages[{index}].tool_calls")
            seen_calls.update(call_ids)
            remaining = call_ids
            pending = (start, len(items), calls, reasoning)
        if pending is not None:
            raise ClientPayloadError("Claude tool calls require all outputs before continuing", param="messages")
        return cls(items, tuple(cycles), reasoning_at)


def _tool_call_id(message: OpenAIMessage, index: int) -> str:
    call_id = next(
        (
            value
            for key in ("tool_call_id", "toolCallId", "call_id")
            if isinstance(value := message.get(key), str) and value
        ),
        None,
    )
    if call_id is None:
        raise ClientPayloadError("tool messages require a call ID", param=f"messages[{index}].tool_call_id")
    return call_id


def _call_from_item(item: dict[str, JsonValue], index: int) -> ChatToolCall:
    call_id, name, arguments = item.get("call_id"), item.get("name"), item.get("arguments")
    if not isinstance(call_id, str) or not isinstance(name, str) or not isinstance(arguments, str):
        raise ClientPayloadError("Invalid Claude tool call", param=f"messages[{index}].tool_calls")
    try:
        decoded = json.loads(arguments)
    except ValueError as exc:
        raise ClientPayloadError("Tool arguments must be JSON", param=f"messages[{index}].tool_calls") from exc
    if not isinstance(decoded, dict):
        raise ClientPayloadError("Tool arguments must encode an object", param=f"messages[{index}].tool_calls")
    return ChatToolCall(call_id, name, arguments)


def _tool_output(message: OpenAIMessage, index: int) -> JsonValue:
    content = message.get("content")
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        raise ClientPayloadError("Tool content must be text or an array", param=f"messages[{index}].content")
    parts: list[JsonValue] = []
    for part_index, part in enumerate(content):
        if isinstance(part, str):
            parts.append({"type": "input_text", "text": part})
            continue
        if not isinstance(part, dict):
            raise ClientPayloadError(
                "Unsupported Claude tool content", param=f"messages[{index}].content[{part_index}]"
            )
        kind = part.get("type", "text" if "text" in part else None)
        if kind in ("text", "input_text", "output_text") and isinstance(part.get("text"), str):
            parts.append({"type": "input_text", "text": part["text"]})
        elif kind in ("image_url", "input_image"):
            image = part.get("image_url")
            url = image.get("url") if isinstance(image, dict) else image
            if not isinstance(url, str):
                raise ClientPayloadError(
                    "Image content requires a URL", param=f"messages[{index}].content[{part_index}]"
                )
            parts.append({"type": "input_image", "image_url": url})
        else:
            raise ClientPayloadError(
                "Unsupported Claude tool content", param=f"messages[{index}].content[{part_index}]"
            )
    return parts


def _chat_visible_output(output: list[JsonValue]) -> list[JsonValue]:
    visible: list[JsonValue] = []
    text_parts: list[str] = []
    for item in output:
        if not isinstance(item, dict):
            continue
        if item.get("type") == "message" and item.get("role") == "assistant":
            parts = item.get("content")
            if isinstance(parts, list):
                text_parts.extend(
                    cast(str, part["text"])
                    for part in parts
                    if isinstance(part, dict)
                    and part.get("type") == "output_text"
                    and isinstance(part.get("text"), str)
                )
        elif item.get("type") == "function_call":
            visible.append(
                {
                    "type": "function_call",
                    "call_id": item.get("call_id"),
                    "name": item.get("name"),
                    "arguments": item.get("arguments"),
                }
            )
    text = "".join(text_parts)
    if text:
        visible.insert(0, {"role": "assistant", "content": [{"type": "output_text", "text": text}]})
    return visible


def _matches_cycle(history: ChatHistory, cycle: ChatToolCycle, retained: ReplayHistory, instructions: str) -> bool:
    if retained.chat_input is None or retained.chat_instructions != instructions:
        return False
    if [*retained.chat_input, *_chat_visible_output(retained.output)] != history.items[: cycle.assistant_end]:
        return False
    results = history.items[cycle.assistant_end : cycle.end]
    call_ids = {call.call_id for call in cycle.calls}
    return len(results) == len(call_ids) and all(
        isinstance(item, dict) and item.get("type") == "function_call_output" and item.get("call_id") in call_ids
        for item in results
    )


@dataclass(frozen=True)
class CycleMatch:
    history: ReplayHistory
    source_id: str | None


@dataclass(frozen=True)
class ChatReplayPlan:
    history: ChatHistory
    matches: dict[int, CycleMatch]
    reasons: dict[int, str]
    active_owner: str | None
    preferred_owner: str | None

    def project(self, *, source_id: str) -> list[JsonValue]:
        items: list[JsonValue] = []
        cursor = 0
        counts: dict[str, int] = {}

        def append_ordinary(start: int, end: int) -> None:
            for index in range(start, end):
                reasoning = self.history.reasoning_at.get(index)
                if reasoning is not None:
                    items.append(_assistant_text("Visible prior reasoning: " + reasoning))
                item = self.history.items[index]
                if (
                    reasoning is not None
                    and isinstance(item, dict)
                    and item.get("role") == "assistant"
                    and item.get("content") in (None, [])
                ):
                    continue
                items.append(item)

        for cycle in self.history.cycles:
            append_ordinary(cursor, cycle.start)
            match = self.matches.get(cycle.start)
            if match is not None and match.source_id == source_id and match.history.input == items:
                items.extend(match.history.output)
                items.extend(self.history.items[cycle.assistant_end : cycle.end])
            else:
                items.extend(_reconstruct_cycle(self.history, cycle))
                reason = (
                    "owner_changed"
                    if match is not None and match.source_id is not None and match.source_id != source_id
                    else "history_changed"
                    if match is not None
                    else self.reasons.get(cycle.start, "missing")
                )
                counts[reason] = counts.get(reason, 0) + 1
            cursor = cycle.end
        append_ordinary(cursor, len(self.history.items))
        if counts:
            reason = next(iter(counts)) if len(counts) == 1 else "mixed"
            logger.info("claude_chat_history_reconstructed reason=%s cycles=%d", reason, sum(counts.values()))
        return items


def _assistant_text(text: str) -> dict[str, JsonValue]:
    return {"role": "assistant", "content": [{"type": "output_text", "text": text}]}


def _reconstruct_cycle(history: ChatHistory, cycle: ChatToolCycle) -> list[JsonValue]:
    assistant_parts: list[JsonValue] = []
    if cycle.reasoning is not None:
        assistant_parts.append({"type": "output_text", "text": "Visible prior reasoning: " + cycle.reasoning})
    for item in history.items[cycle.start : cycle.assistant_end]:
        if not isinstance(item, dict) or item.get("role") != "assistant":
            continue
        content = item.get("content")
        if not isinstance(content, list):
            raise ClientPayloadError("Unsupported assistant content in Claude tool history", param="messages")
        for part in content:
            if not isinstance(part, dict) or part.get("type") != "output_text" or not isinstance(part.get("text"), str):
                raise ClientPayloadError("Unsupported assistant content in Claude tool history", param="messages")
            assistant_parts.append({"type": "output_text", "text": part["text"]})
    call_data = [{"call_id": call.call_id, "name": call.name, "arguments": call.arguments} for call in cycle.calls]
    assistant_parts.append(
        {
            "type": "output_text",
            "text": "Historical tool calls already executed; continue from their results, do not rerun them: "
            + json.dumps(call_data, ensure_ascii=False, separators=(",", ":")),
        }
    )
    projected: list[JsonValue] = [{"role": "assistant", "content": assistant_parts}]
    names = {call.call_id: call.name for call in cycle.calls}
    for item in history.items[cycle.assistant_end : cycle.end]:
        assert isinstance(item, dict)
        call_id = cast(str, item["call_id"])
        output = item["output"]
        result_parts: list[JsonValue] = [
            {
                "type": "input_text",
                "text": "Quoted external result from an already executed tool: "
                + json.dumps({"call_id": call_id, "name": names[call_id]}, ensure_ascii=False, separators=(",", ":")),
            }
        ]
        if isinstance(output, str):
            result_parts.append({"type": "input_text", "text": "text=" + json.dumps(output, ensure_ascii=False)})
        elif isinstance(output, list):
            if not output:
                result_parts.append({"type": "input_text", "text": "parts=[]"})
            for part in output:
                assert isinstance(part, dict)
                if part.get("type") == "input_text":
                    result_parts.append(
                        {"type": "input_text", "text": "text=" + json.dumps(part["text"], ensure_ascii=False)}
                    )
                else:
                    result_parts.append({"type": "input_text", "text": "image from quoted external result follows"})
                    result_parts.append(part)
        projected.append({"role": "user", "content": result_parts})
    return projected


async def plan_chat_replay(
    history: ChatHistory,
    *,
    store: HTTPFallbackReplayStore,
    scope: ReplayScope,
    opaque: ClaudeOpaqueState,
    model: str,
    client_scope: str,
    instructions: str,
) -> ChatReplayPlan:
    records = await store.histories(scope) if scope.api_key_id is not None and history.cycles else []
    matches: dict[int, CycleMatch] = {}
    reasons: dict[int, str] = {}
    for cycle in history.cycles:
        candidates: list[CycleMatch] = []
        for record in records:
            retained = record.history
            if retained.model != model or not _matches_cycle(history, cycle, retained, instructions):
                continue
            if any(isinstance(item, dict) and item.get("type") == "web_search_call" for item in retained.output):
                raise ClientPayloadError(
                    "Claude search state cannot be reconstructed from Chat history", param="messages"
                )
            owner: str | None = None
            for item in retained.output:
                if not isinstance(item, dict) or item.get("type") != "reasoning":
                    continue
                token = item.get("encrypted_content")
                if not isinstance(token, str):
                    continue
                envelope = opaque.authenticate(token, client_scope=client_scope, conversation_id=scope.conversation_id)
                if envelope.block.get("type") == "web_search":
                    raise ClientPayloadError(
                        "Claude search state cannot be reconstructed from Chat history", param="messages"
                    )
                if (envelope.model, envelope.source_id) != (model, retained.account_id):
                    raise ClientPayloadError("Claude Chat replay owner or model mismatch", param="messages")
                owner = envelope.source_id
            candidates.append(CycleMatch(retained, owner))
        if len(candidates) == 1:
            matches[cycle.start] = candidates[0]
        else:
            reasons[cycle.start] = "anonymous" if scope.api_key_id is None else "ambiguous" if candidates else "missing"
    active_owner = next(
        (
            match.source_id
            for cycle in reversed(history.cycles)
            if cycle.end == len(history.items)
            and (match := matches.get(cycle.start)) is not None
            and match.source_id is not None
        ),
        None,
    )
    preferred_owner = next(
        (
            match.source_id
            for cycle in reversed(history.cycles)
            if (match := matches.get(cycle.start)) is not None and match.source_id is not None
        ),
        None,
    )
    return ChatReplayPlan(history, matches, reasons, active_owner, preferred_owner)
