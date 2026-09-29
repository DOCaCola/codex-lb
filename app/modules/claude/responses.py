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
from app.modules.claude.search import url_citations
from app.modules.claude.tool_schema import MAX_TOOL_ARGUMENT_BYTES


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
    search_enabled: bool = False
    chat_reasoning: bool = False
    response_id: str = ""
    created_at: int = field(default_factory=lambda: int(time.time()))
    sequence: int = 0
    blocks: dict[int, dict[str, JsonValue]] = field(default_factory=dict)
    outputs: dict[int, dict[str, JsonValue]] = field(default_factory=dict)
    partial_json: dict[int, str] = field(default_factory=dict)
    partial_json_bytes: dict[int, int] = field(default_factory=dict)
    search_calls: dict[str, tuple[int, dict[str, JsonValue]]] = field(default_factory=dict)
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
            reason = (
                "max_output_tokens"
                if self.stop_reason == "max_tokens"
                else "content_filter"
                if self.stop_reason == "refusal"
                else self.stop_reason
            )
            incomplete = {"reason": reason}
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
                "content": [
                    {"type": "output_text", "text": block.get("text", ""), "annotations": url_citations(block)}
                ],
            }
        if kind == "server_tool_use":
            if not self.search_enabled or block.get("name") != "web_search" or not isinstance(block.get("id"), str):
                raise ClaudeError("Claude returned an undeclared server tool")
            arguments = block.get("input", {})
            if not isinstance(arguments, dict) or (final and not isinstance(arguments.get("query"), str)):
                raise ClaudeError("Invalid Claude search query")
            return {
                "id": item_id,
                "type": "web_search_call",
                "status": "searching" if final else "in_progress",
                "action": {"type": "search", "query": arguments.get("query", "")},
            }
        if kind == "web_search_tool_result":
            call_id = block.get("tool_use_id")
            if not isinstance(call_id, str) or call_id not in self.search_calls:
                raise ClaudeError("Claude search result has no matching server call")
            content = block.get("content")
            if not isinstance(content, list):
                raise ClaudeError("Claude web search failed")
            for result in content:
                if not isinstance(result, dict) or result.get("type") != "web_search_result":
                    raise ClaudeError("Unsupported Claude web search result")
            result_item: dict[str, JsonValue] = {"id": item_id, "type": "reasoning", "summary": []}
            if final:
                call_index, call = self.search_calls[call_id]
                result_item["encrypted_content"] = self.opaque.encode(
                    self.scope,
                    {
                        "type": "web_search",
                        "item_id": self.outputs[call_index]["id"],
                        "blocks": [call, block],
                    },
                )
            return result_item
        if kind in ("thinking", "redacted_thinking"):
            result: dict[str, JsonValue] = {"id": item_id, "type": "reasoning", "summary": []}
            if final and self.chat_reasoning and kind == "thinking" and isinstance(block.get("thinking"), str):
                result["summary"] = [{"type": "summary_text", "text": block["thinking"]}]
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
                if final and identity.arguments is not None:
                    arguments = identity.arguments.decode(arguments)
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
            if self.blocks or self.search_calls or self.stop_reason is None:
                raise ClaudeError("Claude stopped before closing its content and stop reason")
            if self.stop_reason not in ("end_turn", "stop_sequence", "tool_use", "max_tokens", "pause_turn", "refusal"):
                raise ClaudeError("Unknown Claude stop reason")
            self.stopped = True
            incomplete_reasons = (
                ("max_tokens", "pause_turn", "refusal") if self.chat_reasoning else ("max_tokens", "pause_turn")
            )
            status = "incomplete" if self.stop_reason in incomplete_reasons else "completed"
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
            if block.get("type") == "server_tool_use":
                events.append(
                    self.event("response.web_search_call.in_progress", item_id=item["id"], output_index=index)
                )
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
            if delta_type == "citations_delta" and block.get("type") == "text":
                citations = block.setdefault("citations", [])
                if not isinstance(citations, list):
                    raise ClaudeError("Invalid Claude citations")
                citations.append(delta.get("citation"))
                annotation = url_citations(block)[-1]
                return [
                    self.event(
                        "response.output_text.annotation.added",
                        item_id=self.outputs[index]["id"],
                        output_index=index,
                        content_index=0,
                        annotation_index=len(citations) - 1,
                        annotation=annotation,
                    )
                ]
            if delta_type == "input_json_delta" and block.get("type") in ("tool_use", "server_tool_use"):
                piece = delta.get("partial_json")
                if not isinstance(piece, str):
                    raise ClaudeError("Invalid Claude tool JSON delta")
                identity = self.tools.get(str(block.get("name")))
                wrapped = identity is not None and identity.arguments is not None
                if wrapped:
                    size = self.partial_json_bytes.get(index, 0) + len(piece.encode())
                    if size > MAX_TOOL_ARGUMENT_BYTES:
                        raise ClaudeError("Claude wrapped tool arguments exceeded the size limit")
                    self.partial_json_bytes[index] = size
                self.partial_json[index] = self.partial_json.get(index, "") + piece
                if wrapped:
                    return []  # The private envelope must never reach client deltas.
                item = self.outputs[index]
                if item["type"] in ("custom_tool_call", "web_search_call"):
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
            if field_name == "thinking" and self.chat_reasoning:
                return [
                    self.event(
                        "response.reasoning_summary_text.delta",
                        item_id=self.outputs[index]["id"],
                        output_index=index,
                        summary_index=0,
                        delta=delta[field_name],
                    )
                ]
            return []
        if kind != "content_block_stop":
            raise ClaudeError("Unsupported Claude stream event")
        if index in self.partial_json:
            self.partial_json_bytes.pop(index, None)
            try:
                raw = self.partial_json.pop(index)
                identity = self.tools.get(str(block.get("name")))
                block["input"] = (
                    identity.arguments.parse(raw)
                    if identity is not None and identity.arguments is not None
                    else json.loads(raw)
                )
            except ValueError as exc:
                raise ClaudeError("Claude returned invalid tool JSON") from exc
        item = self._item(index, self.blocks.pop(index), final=True)
        self.outputs[index] = item
        events = []
        if block.get("type") == "server_tool_use":
            call_id = block["id"]
            assert isinstance(call_id, str)
            if call_id in self.search_calls:
                raise ClaudeError("Duplicate Claude server call")
            self.search_calls[call_id] = (index, deepcopy(block))
            return [self.event("response.web_search_call.searching", item_id=item["id"], output_index=index)]
        if block.get("type") == "web_search_tool_result":
            call_id = block["tool_use_id"]
            assert isinstance(call_id, str)
            call_index, _ = self.search_calls.pop(call_id)
            search_item = self.outputs[call_index]
            search_item["status"] = "completed"
            events.extend(
                [
                    self.event(
                        "response.web_search_call.completed", item_id=search_item["id"], output_index=call_index
                    ),
                    self.event("response.output_item.done", output_index=call_index, item=deepcopy(search_item)),
                ]
            )
        if item["type"] == "message":
            part = {"type": "output_text", "text": block.get("text", ""), "annotations": url_citations(block)}
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
            identity = self.tools[str(block["name"])]
            if identity.arguments is not None:
                events.append(
                    self.event(
                        "response.function_call_arguments.delta",
                        item_id=item["id"],
                        output_index=index,
                        delta=item["arguments"],
                    )
                )
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
