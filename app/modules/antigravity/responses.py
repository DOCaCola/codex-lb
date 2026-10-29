"""Cloud Code (Gemini) SSE projection onto Responses events.

Each SSE line is {"response": {candidates, usageMetadata, modelVersion, responseId}, "traceId"}
(native CLI capture). Thought parts become reasoning items whose summary is the
readable thought and whose encrypted content seals the step's first signature for
same-channel replay. Text becomes one assistant message per run; its phase is
commentary when a call follows and final_answer when the turn ends.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from copy import deepcopy
from dataclasses import dataclass, field
from typing import cast

from pydantic import JsonValue

from app.core.utils.request_id import get_request_id
from app.modules.antigravity.errors import AntigravityError
from app.modules.antigravity.opaque import AntigravityOpaqueState, ThoughtScope
from app.modules.antigravity.tool_names import GoogleToolNames
from app.modules.claude.code_mode import CODE_MODE_EXEC, code_mode_helper, custom_tool_input
from app.modules.claude.credentials import ClaudeError
from app.modules.claude.responses import _declared_tools, _loggable_tool_name, _tool_name_hash

logger = logging.getLogger(__name__)

_FILTERED = frozenset({"SAFETY", "RECITATION", "BLOCKLIST", "PROHIBITED_CONTENT", "SPII", "IMAGE_SAFETY", "LANGUAGE"})
_MALFORMED = frozenset({"MALFORMED_FUNCTION_CALL", "UNEXPECTED_TOOL_CALL", "TOO_MANY_TOOL_CALLS"})


class EmptyCompletion(AntigravityError):
    """A finished generation with neither visible text nor a call; retried once before any output."""

    def __init__(self) -> None:
        super().__init__(
            "Antigravity finished without visible output or a tool call",
            code="empty_completion",
            status_code=502,
        )


@dataclass
class Usage:
    prompt: int = 0
    cached: int = 0
    candidates: int = 0
    thoughts: int = 0

    def responses(self) -> dict[str, JsonValue]:
        output = self.candidates + self.thoughts
        return {
            "input_tokens": self.prompt,
            "input_tokens_details": {"cached_tokens": self.cached},
            "output_tokens": output,
            "output_tokens_details": {"reasoning_tokens": self.thoughts},
            "total_tokens": self.prompt + output,
        }


def _count(metadata: dict[str, JsonValue], key: str) -> int:
    value = metadata.get(key, 0)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise AntigravityError("Antigravity returned invalid usage metadata", code="invalid_upstream_response")
    return value


@dataclass
class GeminiProjection:
    model: str
    scope: ThoughtScope
    tools: GoogleToolNames
    opaque: AntigravityOpaqueState
    show_summary: bool
    response_id: str = ""
    created_at: int = field(default_factory=lambda: int(time.time()))
    sequence: int = 0
    outputs: dict[int, dict[str, JsonValue]] = field(default_factory=dict)
    usage: Usage = field(default_factory=Usage)
    # Usage of an earlier attempt of this same response (the empty-completion retry), billed with it.
    prior: Usage = field(default_factory=Usage)
    # The open reasoning item (output index, accumulated thought) or assistant message.
    thought: tuple[int, str] | None = None
    message: tuple[int, str] | None = None
    signature: str | None = None
    signature_sealed: bool = False
    calls: int = 0
    text_seen: bool = False
    finish_reason: str | None = None
    started: bool = False
    stopped: bool = False

    @property
    def visible(self) -> bool:
        """Whether the client has been shown generated content (text or a call)."""
        return self.text_seen or self.calls > 0

    def event(self, kind: str, **fields: JsonValue) -> dict[str, JsonValue]:
        result: dict[str, JsonValue] = {"type": kind, "sequence_number": self.sequence, **fields}
        self.sequence += 1
        return result

    def envelope(self, status: str, *, incomplete: str | None = None) -> dict[str, JsonValue]:
        return {
            "id": self.response_id,
            "object": "response",
            "created_at": self.created_at,
            "model": self.model,
            "status": status,
            "output": list(self.outputs.values()),
            "usage": self.usage.responses(),
            "error": None,
            "incomplete_details": {"reason": incomplete} if incomplete else None,
        }

    def _slot(self) -> int:
        return len(self.outputs)

    def _start(self, chunk: dict[str, JsonValue]) -> list[dict[str, JsonValue]]:
        self.started = True
        upstream = chunk.get("responseId")
        self.response_id = "resp_" + (upstream if isinstance(upstream, str) and upstream else uuid.uuid4().hex)
        return [
            self.event("response.created", response=self.envelope("in_progress")),
            self.event("response.in_progress", response=self.envelope("in_progress")),
        ]

    def consume(self, line: dict[str, JsonValue]) -> list[dict[str, JsonValue]]:
        if self.stopped:
            raise AntigravityError("Antigravity emitted data after its finish reason", code="invalid_upstream_response")
        if "error" in line:
            raise AntigravityError("Antigravity reported an error mid-stream", code="upstream_error", status_code=502)
        chunk = line.get("response")
        if not isinstance(chunk, dict):
            raise AntigravityError("Antigravity stream line has no response", code="invalid_upstream_response")
        events = [] if self.started else self._start(chunk)
        metadata = chunk.get("usageMetadata")
        if isinstance(metadata, dict):
            self.usage = Usage(
                prompt=self.prior.prompt + _count(metadata, "promptTokenCount"),
                cached=self.prior.cached + _count(metadata, "cachedContentTokenCount"),
                candidates=self.prior.candidates + _count(metadata, "candidatesTokenCount"),
                thoughts=self.prior.thoughts + _count(metadata, "thoughtsTokenCount"),
            )
        feedback = chunk.get("promptFeedback")
        if isinstance(feedback, dict) and isinstance(feedback.get("blockReason"), str):
            self.finish_reason = "SAFETY"
            return [*events, *self._finish()]
        candidates = chunk.get("candidates", [])
        if not isinstance(candidates, list) or len(candidates) > 1:
            raise AntigravityError(
                "Antigravity returned an unexpected candidate list", code="invalid_upstream_response"
            )
        if not candidates:
            return events
        candidate = candidates[0]
        if not isinstance(candidate, dict):
            raise AntigravityError("Antigravity returned an invalid candidate", code="invalid_upstream_response")
        content = candidate.get("content")
        parts = content.get("parts", []) if isinstance(content, dict) else []
        if not isinstance(parts, list):
            raise AntigravityError("Antigravity returned invalid content parts", code="invalid_upstream_response")
        for part in parts:
            if not isinstance(part, dict):
                raise AntigravityError("Antigravity returned an invalid content part", code="invalid_upstream_response")
            events.extend(self._part(part))
        reason = candidate.get("finishReason")
        if isinstance(reason, str) and reason:
            self.finish_reason = reason
            events.extend(self._finish())
        return events

    def _part(self, part: dict[str, JsonValue]) -> list[dict[str, JsonValue]]:
        signature = part.get("thoughtSignature")
        if isinstance(signature, str) and signature and self.signature is None:
            self.signature = signature
        events: list[dict[str, JsonValue]] = []
        if part.get("thought") is True:
            text = part.get("text", "")
            if not isinstance(text, str):
                raise AntigravityError("Antigravity returned an invalid thought", code="invalid_upstream_response")
            events.extend(self._close_message("commentary"))
            if self.thought is None:
                slot = self._slot()
                item: dict[str, JsonValue] = {"id": f"{self.response_id}_{slot}", "type": "reasoning", "summary": []}
                self.outputs[slot] = item
                self.thought = (slot, "")
                events.append(self.event("response.output_item.added", output_index=slot, item=deepcopy(item)))
                if self.show_summary:
                    events.append(
                        self.event(
                            "response.reasoning_summary_part.added",
                            item_id=item["id"],
                            output_index=slot,
                            summary_index=0,
                            part={"type": "summary_text", "text": ""},
                        )
                    )
            slot, previous = self.thought
            self.thought = (slot, previous + text)
            if text and self.show_summary:
                events.append(
                    self.event(
                        "response.reasoning_summary_text.delta",
                        item_id=self.outputs[slot]["id"],
                        output_index=slot,
                        summary_index=0,
                        delta=text,
                    )
                )
            return events
        if "functionCall" in part:
            events.extend(self._close_thought())
            events.extend(self._close_message("commentary"))
            events.extend(self._seal_signature())
            events.extend(self._call(part["functionCall"]))
            return events
        if "text" in part:
            text = part["text"]
            if not isinstance(text, str):
                raise AntigravityError("Antigravity returned invalid text", code="invalid_upstream_response")
            events.extend(self._close_thought())
            if not text:
                return events
            if self.message is None:
                slot = self._slot()
                part_item: dict[str, JsonValue] = {"type": "output_text", "text": "", "annotations": []}
                message: dict[str, JsonValue] = {
                    "id": f"{self.response_id}_{slot}",
                    "type": "message",
                    "role": "assistant",
                    "status": "in_progress",
                    "content": [deepcopy(part_item)],
                }
                self.outputs[slot] = message
                self.message = (slot, "")
                events.append(self.event("response.output_item.added", output_index=slot, item=deepcopy(message)))
                events.append(
                    self.event(
                        "response.content_part.added",
                        item_id=message["id"],
                        output_index=slot,
                        content_index=0,
                        part=part_item,
                    )
                )
            slot, previous = self.message
            self.message = (slot, previous + text)
            self.text_seen = True
            events.append(
                self.event(
                    "response.output_text.delta",
                    item_id=self.outputs[slot]["id"],
                    output_index=slot,
                    content_index=0,
                    delta=text,
                )
            )
            return events
        if part.keys() <= {"thoughtSignature"}:
            return events
        raise AntigravityError("Antigravity returned an unsupported content part", code="invalid_upstream_response")

    def _close_thought(self) -> list[dict[str, JsonValue]]:
        if self.thought is None:
            return []
        slot, text = self.thought
        self.thought = None
        item = self.outputs[slot]
        events: list[dict[str, JsonValue]] = []
        if self.show_summary:
            summary: dict[str, JsonValue] = {"type": "summary_text", "text": text}
            item["summary"] = [summary]
            events.append(
                self.event(
                    "response.reasoning_summary_text.done",
                    item_id=item["id"],
                    output_index=slot,
                    summary_index=0,
                    text=text,
                )
            )
            events.append(
                self.event(
                    "response.reasoning_summary_part.done",
                    item_id=item["id"],
                    output_index=slot,
                    summary_index=0,
                    part=deepcopy(summary),
                )
            )
        item["encrypted_content"] = self.opaque.seal(self.scope, text=text, signature=self.signature)
        self.signature_sealed |= self.signature is not None
        events.append(self.event("response.output_item.done", output_index=slot, item=deepcopy(item)))
        return events

    def _seal_signature(self) -> list[dict[str, JsonValue]]:
        """Carry a signature first seen on a call in its own reasoning item, ahead of that call."""
        if self.signature is None or self.signature_sealed:
            return []
        slot = self._slot()
        item: dict[str, JsonValue] = {"id": f"{self.response_id}_{slot}", "type": "reasoning", "summary": []}
        self.outputs[slot] = item
        events = [self.event("response.output_item.added", output_index=slot, item=deepcopy(item))]
        item["encrypted_content"] = self.opaque.seal(self.scope, text="", signature=self.signature)
        self.signature_sealed = True
        events.append(self.event("response.output_item.done", output_index=slot, item=deepcopy(item)))
        return events

    def _close_message(self, phase: str | None) -> list[dict[str, JsonValue]]:
        if self.message is None:
            return []
        slot, text = self.message
        self.message = None
        message = self.outputs[slot]
        part: dict[str, JsonValue] = {"type": "output_text", "text": text, "annotations": []}
        message["content"] = [deepcopy(part)]
        message["status"] = "completed"
        if phase is not None:
            message["phase"] = phase
        return [
            self.event(
                "response.output_text.done", item_id=message["id"], output_index=slot, content_index=0, text=text
            ),
            self.event(
                "response.content_part.done", item_id=message["id"], output_index=slot, content_index=0, part=part
            ),
            self.event("response.output_item.done", output_index=slot, item=deepcopy(message)),
        ]

    def _call(self, call: JsonValue) -> list[dict[str, JsonValue]]:
        if not isinstance(call, dict) or not isinstance(call.get("name"), str):
            raise AntigravityError("Antigravity returned an invalid function call", code="invalid_upstream_response")
        name = cast(str, call["name"])
        arguments = call.get("args", {})
        if not isinstance(arguments, dict):
            raise AntigravityError(
                "Antigravity function call arguments must be an object", code="invalid_upstream_response"
            )
        identity = self.tools.resolve(name)
        helper = code_mode_helper(self.tools, name) if identity is None else None
        if helper is not None:
            identity = self.tools.identity(CODE_MODE_EXEC)
        if identity is None:
            logger.warning(
                "antigravity_undeclared_tool source_id=%s model=%s response_id=%s declared_count=%d "
                "tool_name=%s tool_name_hash=%s declared_tools=%s",
                self.scope.source_id,
                self.model,
                self.response_id,
                len(self.tools),
                _loggable_tool_name(name),
                _tool_name_hash(name),
                _declared_tools(self.tools),
            )
            raise AntigravityError("Antigravity returned an undeclared tool", code="invalid_upstream_response")
        upstream_id = call.get("id")
        call_id = upstream_id if isinstance(upstream_id, str) and upstream_id else "call_" + uuid.uuid4().hex[:24]
        slot = self._slot()
        item_id = f"{self.response_id}_{slot}"
        try:
            if identity.arguments is not None and not identity.custom:
                arguments = identity.arguments.decode(arguments)
        except ClaudeError as exc:
            raise AntigravityError(str(exc), code="invalid_upstream_response") from exc
        events: list[dict[str, JsonValue]] = []
        if identity.search:
            item: dict[str, JsonValue] = {
                "id": item_id,
                "type": "tool_search_call",
                "call_id": call_id,
                "execution": "client",
                "status": "completed",
                "arguments": arguments,
            }
            events.append(
                self.event("response.output_item.added", output_index=slot, item={**item, "status": "in_progress"})
            )
        elif identity.custom:
            tool_input = custom_tool_input(self.tools, identity, arguments, helper)
            if tool_input.repairs or tool_input.shell_shaped:
                logger.info(
                    "antigravity_tool_input_repair source_id=%s model=%s response_id=%s tool=%s repairs=%s",
                    self.scope.source_id,
                    self.model,
                    self.response_id,
                    _loggable_tool_name(identity.name),
                    ",".join(tool_input.repairs) or "none",
                )
            item = {"id": item_id, "type": "custom_tool_call", "call_id": call_id, "name": identity.name}
            if identity.namespace is not None:
                item["namespace"] = identity.namespace
            events.append(
                self.event(
                    "response.output_item.added", output_index=slot, item={**item, "status": "in_progress", "input": ""}
                )
            )
            item.update(status="completed", input=tool_input.text)
            events.append(
                self.event(
                    "response.custom_tool_call_input.delta", item_id=item_id, output_index=slot, delta=tool_input.text
                )
            )
            events.append(
                self.event(
                    "response.custom_tool_call_input.done", item_id=item_id, output_index=slot, input=tool_input.text
                )
            )
        else:
            text = json.dumps(arguments, ensure_ascii=False, separators=(",", ":"))
            item = {"id": item_id, "type": "function_call", "call_id": call_id, "name": identity.name}
            if identity.namespace is not None:
                item["namespace"] = identity.namespace
            events.append(
                self.event(
                    "response.output_item.added",
                    output_index=slot,
                    item={**item, "status": "in_progress", "arguments": ""},
                )
            )
            item.update(status="completed", arguments=text)
            events.append(
                self.event("response.function_call_arguments.delta", item_id=item_id, output_index=slot, delta=text)
            )
            events.append(
                self.event("response.function_call_arguments.done", item_id=item_id, output_index=slot, arguments=text)
            )
        self.outputs[slot] = item
        self.calls += 1
        events.append(self.event("response.output_item.done", output_index=slot, item=deepcopy(item)))
        return events

    def _finish(self) -> list[dict[str, JsonValue]]:
        reason = self.finish_reason
        logger.info(
            "antigravity_finish request_id=%s response_id=%s model=%s finish_reason=%s calls=%d text=%s "
            "output_tokens=%d thought_tokens=%d",
            get_request_id(),
            self.response_id,
            self.model,
            reason,
            self.calls,
            self.text_seen,
            self.usage.candidates,
            self.usage.thoughts,
        )
        if reason in _MALFORMED:
            raise AntigravityError(
                f"Antigravity produced an invalid tool call ({reason})", code="invalid_upstream_response"
            )
        events = self._close_thought()
        self.stopped = True
        if reason == "STOP":
            if not self.visible:
                raise EmptyCompletion()
            events.extend(self._close_message("commentary" if self.calls else "final_answer"))
            return [*events, self.event("response.completed", response=self.envelope("completed"))]
        if reason == "MAX_TOKENS":
            events.extend(self._close_message(None))
            return [
                *events,
                self.event("response.incomplete", response=self.envelope("incomplete", incomplete="max_output_tokens")),
            ]
        if reason in _FILTERED:
            events.extend(self._close_message(None))
            return [
                *events,
                self.event("response.incomplete", response=self.envelope("incomplete", incomplete="content_filter")),
            ]
        raise AntigravityError(f"Antigravity stopped with finish reason {reason}", code="invalid_upstream_response")

    def interrupt(self) -> list[dict[str, JsonValue]]:
        """Close the finished message of a stream ending without a finish reason; its phase stays unknown."""
        return self._close_message(None)
