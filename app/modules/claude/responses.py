"""Messages response and SSE lifecycle projection onto Responses events."""

from __future__ import annotations

import json
import time
from copy import deepcopy
from dataclasses import dataclass, field

from pydantic import BaseModel, Field, JsonValue

from app.modules.claude.credentials import ClaudeError
from app.modules.claude.opaque import ClaudeOpaqueState, OpaqueScope
from app.modules.claude.protocol import ToolIdentity


class Usage(BaseModel):
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    cache_read_input_tokens: int = Field(default=0, ge=0)
    cache_creation_input_tokens: int = Field(default=0, ge=0)

    def responses(self) -> dict[str, JsonValue]:
        total_input = self.input_tokens + self.cache_read_input_tokens + self.cache_creation_input_tokens
        return {
            "input_tokens": total_input,
            "output_tokens": self.output_tokens,
            "total_tokens": total_input + self.output_tokens,
            "input_tokens_details": {
                "cached_tokens": self.cache_read_input_tokens,
                "cache_creation_tokens": self.cache_creation_input_tokens,
            },
        }


@dataclass
class ResponsesProjection:
    scope: OpaqueScope
    tools: dict[str, ToolIdentity]
    opaque: ClaudeOpaqueState
    response_id: str = ""
    created_at: int = field(default_factory=lambda: int(time.time()))
    sequence: int = 0
    blocks: dict[int, dict[str, JsonValue]] = field(default_factory=dict)
    outputs: dict[int, dict[str, JsonValue]] = field(default_factory=dict)
    partial_json: dict[int, str] = field(default_factory=dict)
    usage: Usage = field(default_factory=Usage)
    stop_reason: str | None = None
    started: bool = False
    stopped: bool = False

    def event(self, kind: str, **fields: JsonValue) -> dict[str, JsonValue]:
        result: dict[str, JsonValue] = {"type": kind, "sequence_number": self.sequence, **fields}
        self.sequence += 1
        return result

    def envelope(self, status: str) -> dict[str, JsonValue]:
        incomplete = None
        if status == "incomplete":
            incomplete = {"reason": "max_output_tokens" if self.stop_reason == "max_tokens" else self.stop_reason}
        return {
            "id": self.response_id,
            "object": "response",
            "created_at": self.created_at,
            "model": self.scope.model,
            "status": status,
            "output": list(self.outputs.values()),
            "usage": self.usage.responses(),
            "error": None,
            "incomplete_details": incomplete,
        }

    def _item(self, index: int, block: dict[str, JsonValue], *, final: bool) -> dict[str, JsonValue]:
        item_id = f"{self.response_id}_{index}"
        kind = block.get("type")
        if kind == "text":
            return {
                "id": item_id,
                "type": "message",
                "role": "assistant",
                "status": "completed" if final else "in_progress",
                "content": [{"type": "output_text", "text": block.get("text", ""), "annotations": []}],
            }
        if kind in ("thinking", "redacted_thinking"):
            result: dict[str, JsonValue] = {"id": item_id, "type": "reasoning", "summary": []}
            if final:
                result["encrypted_content"] = self.opaque.encode(self.scope, block)
            return result
        if kind == "tool_use":
            name = block.get("name")
            identity = self.tools.get(name) if isinstance(name, str) else None
            if identity is None:
                raise ClaudeError("Claude returned an undeclared tool")
            arguments = block.get("input", {})
            if not isinstance(arguments, dict):
                raise ClaudeError("Claude tool input must be an object")
            result = {
                "id": item_id,
                "call_id": block.get("id"),
                "name": identity.name,
                "type": "custom_tool_call" if identity.custom else "function_call",
                "status": "completed" if final else "in_progress",
            }
            if identity.namespace is not None:
                result["namespace"] = identity.namespace
            if identity.custom:
                value = arguments.get("input", "")
                if not isinstance(value, str):
                    raise ClaudeError("Claude custom tool input must be text")
                result["input"] = value
            else:
                result["arguments"] = json.dumps(arguments, ensure_ascii=False, separators=(",", ":")) if final else ""
            return result
        raise ClaudeError("Claude returned an unsupported content block")

    def consume(self, event: dict[str, JsonValue]) -> list[dict[str, JsonValue]]:
        kind = event.get("type")
        if self.stopped:
            raise ClaudeError("Claude emitted events after its terminal event")
        if kind == "ping":
            return []
        if kind == "error":
            self.stopped = True
            return [self.event("error", error=event.get("error"))]
        if kind == "message_start":
            message = event.get("message")
            if self.started or not isinstance(message, dict) or not isinstance(message.get("id"), str):
                raise ClaudeError("Invalid Claude message_start")
            self.started = True
            self.response_id = "resp_" + str(message["id"])
            self.usage = Usage.model_validate(message.get("usage", {}))
            return [
                self.event("response.created", response=self.envelope("in_progress")),
                self.event("response.in_progress", response=self.envelope("in_progress")),
            ]
        if not self.started:
            raise ClaudeError("Claude stream did not begin with message_start")
        if kind == "message_delta":
            delta = event.get("delta")
            if not isinstance(delta, dict) or not isinstance(delta.get("stop_reason"), str):
                raise ClaudeError("Invalid Claude message_delta")
            self.stop_reason = str(delta["stop_reason"])
            update = event.get("usage", {})
            if not isinstance(update, dict):
                raise ClaudeError("Invalid Claude stream usage")
            self.usage = Usage.model_validate({**self.usage.model_dump(), **update})
            return []
        if kind == "message_stop":
            if self.blocks or self.stop_reason is None:
                raise ClaudeError("Claude stopped before closing its content and stop reason")
            if self.stop_reason not in ("end_turn", "stop_sequence", "tool_use", "max_tokens", "pause_turn", "refusal"):
                raise ClaudeError("Unknown Claude stop reason")
            self.stopped = True
            status = "incomplete" if self.stop_reason in ("max_tokens", "pause_turn") else "completed"
            return [self.event(f"response.{status}", response=self.envelope(status))]
        index = event.get("index")
        if not isinstance(index, int) or isinstance(index, bool) or index < 0:
            raise ClaudeError("Invalid Claude content index")
        if kind == "content_block_start":
            block = event.get("content_block")
            if not isinstance(block, dict) or index in self.outputs or index != len(self.outputs):
                raise ClaudeError("Invalid Claude content_block_start")
            self.blocks[index] = deepcopy(block)
            item = self._item(index, block, final=False)
            self.outputs[index] = item
            events = [self.event("response.output_item.added", output_index=index, item=deepcopy(item))]
            if block.get("type") == "text":
                events.append(
                    self.event(
                        "response.content_part.added",
                        item_id=item["id"],
                        output_index=index,
                        content_index=0,
                        part={"type": "output_text", "text": "", "annotations": []},
                    )
                )
            return events
        if index not in self.blocks:
            raise ClaudeError("Claude stream refers to an unopened content block")
        block = self.blocks[index]
        if kind == "content_block_delta":
            delta = event.get("delta")
            if not isinstance(delta, dict):
                raise ClaudeError("Invalid Claude content delta")
            delta_type = delta.get("type")
            if delta_type == "input_json_delta" and block.get("type") == "tool_use":
                piece = delta.get("partial_json")
                if not isinstance(piece, str):
                    raise ClaudeError("Invalid Claude tool JSON delta")
                self.partial_json[index] = self.partial_json.get(index, "") + piece
                item = self.outputs[index]
                if item["type"] == "custom_tool_call":
                    return []  # JSON escapes must be decoded before emitting free-form input.
                return [
                    self.event(
                        "response.function_call_arguments.delta", item_id=item["id"], output_index=index, delta=piece
                    )
                ]
            field_name = {"text_delta": "text", "thinking_delta": "thinking", "signature_delta": "signature"}.get(
                str(delta_type)
            )
            if field_name is None or not isinstance(delta.get(field_name), str):
                raise ClaudeError("Unsupported Claude content delta")
            valid_type = "text" if field_name == "text" else "thinking"
            if block.get("type") != valid_type:
                raise ClaudeError("Claude delta does not match its content block")
            block[field_name] = str(block.get(field_name, "")) + str(delta[field_name])
            if field_name == "text":
                return [
                    self.event(
                        "response.output_text.delta",
                        item_id=self.outputs[index]["id"],
                        output_index=index,
                        content_index=0,
                        delta=delta[field_name],
                    )
                ]
            return []
        if kind != "content_block_stop":
            raise ClaudeError("Unsupported Claude stream event")
        if index in self.partial_json:
            try:
                block["input"] = json.loads(self.partial_json.pop(index))
            except ValueError as exc:
                raise ClaudeError("Claude returned invalid tool JSON") from exc
        item = self._item(index, self.blocks.pop(index), final=True)
        self.outputs[index] = item
        events = []
        if item["type"] == "message":
            part = {"type": "output_text", "text": block.get("text", ""), "annotations": []}
            events.extend(
                [
                    self.event(
                        "response.output_text.done",
                        item_id=item["id"],
                        output_index=index,
                        content_index=0,
                        text=part["text"],
                    ),
                    self.event(
                        "response.content_part.done", item_id=item["id"], output_index=index, content_index=0, part=part
                    ),
                ]
            )
        elif item["type"] == "function_call":
            events.append(
                self.event(
                    "response.function_call_arguments.done",
                    item_id=item["id"],
                    output_index=index,
                    arguments=item["arguments"],
                )
            )
        elif item["type"] == "custom_tool_call":
            events.extend(
                [
                    self.event(
                        "response.custom_tool_call_input.delta",
                        item_id=item["id"],
                        output_index=index,
                        delta=item["input"],
                    ),
                    self.event(
                        "response.custom_tool_call_input.done",
                        item_id=item["id"],
                        output_index=index,
                        input=item["input"],
                    ),
                ]
            )
        events.append(self.event("response.output_item.done", output_index=index, item=deepcopy(item)))
        return events

    def complete(self, message: dict[str, JsonValue]) -> dict[str, JsonValue]:
        content = message.get("content")
        if not isinstance(content, list):
            raise ClaudeError("Invalid Claude message content")
        self.consume({"type": "message_start", "message": {"id": message.get("id"), "usage": message.get("usage", {})}})
        for index, block in enumerate(content):
            self.consume({"type": "content_block_start", "index": index, "content_block": block})
            self.consume({"type": "content_block_stop", "index": index})
        self.consume(
            {
                "type": "message_delta",
                "delta": {"stop_reason": message.get("stop_reason")},
                "usage": message.get("usage", {}),
            }
        )
        terminal = self.consume({"type": "message_stop"})[0]["response"]
        assert isinstance(terminal, dict)
        return terminal
