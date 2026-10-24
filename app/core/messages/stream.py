"""Project a Responses event stream onto the Anthropic Messages stream.

Based on agent-lb's projection with CLIProxyAPI's fixes: one thinking block per reasoning item,
commentary-phase messages as unsigned thinking, tool-call start deferred until the name is
known, hosted web search blocks, and cache-adjusted usage.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Literal

from app.core.messages.envelope import ReasoningEnvelope, seal_reasoning
from app.core.messages.errors import anthropic_error
from app.core.types import JsonValue

type BlockKind = Literal["thinking", "text", "tool_use"]

_TERMINAL_SUCCESS = frozenset({"response.completed", "response.incomplete"})
_TERMINAL_FAILURE = frozenset({"response.failed", "error"})
_REASONING_DELTAS = frozenset({"response.reasoning_summary_text.delta", "response.reasoning_text.delta"})


@dataclass(slots=True)
class _Item:
    item_type: str
    phase: str | None = None
    streamed: bool = False
    part_index: int | None = None
    call_id: str | None = None
    name: str | None = None
    arguments: list[str] = field(default_factory=list)


@dataclass(slots=True)
class _OpenBlock:
    kind: BlockKind
    item_id: str


class MessagesStreamProjector:
    """Stateful Responses-to-Messages projection for one response.

    `feed` returns the Messages events for one upstream event, excluding `message_start`, which
    the caller emits once it has decided to stream. A failure sets `error` (status and Anthropic
    envelope); before any output it also sets `failure` instead of producing an in-band event.
    """

    def __init__(self, *, model: str, reported_model: str, tool_names: Mapping[str, str], envelope_key: bytes) -> None:
        self._model = model
        self._reported_model = reported_model
        self._tool_names = tool_names
        self._envelope_key = envelope_key
        self._message_id: str | None = None
        self._items: dict[str, _Item] = {}
        self._open: _OpenBlock | None = None
        self._index = 0
        self._tool_used = False
        self.has_output = False
        self.terminal = False
        self.error: tuple[int, dict[str, JsonValue]] | None = None
        self.failure: tuple[int, dict[str, JsonValue]] | None = None

    def message_start(self) -> dict[str, JsonValue]:
        return {
            "type": "message_start",
            "message": {
                "id": self._message_id or f"msg_{uuid.uuid4().hex}",
                "type": "message",
                "role": "assistant",
                "model": self._reported_model,
                "content": [],
                "stop_reason": None,
                "stop_sequence": None,
                "usage": {"input_tokens": 0, "output_tokens": 0},
            },
        }

    def feed(self, event: Mapping[str, JsonValue]) -> list[dict[str, JsonValue]]:
        if self.terminal:
            return []
        event_type = event.get("type")
        out: list[dict[str, JsonValue]] = []
        if event_type in ("response.created", "response.in_progress"):
            self._capture_id(event.get("response"))
        elif event_type == "response.output_item.added":
            self._item_added(event.get("item"), out)
        elif event_type in _REASONING_DELTAS:
            self._reasoning_delta(event, out)
        elif event_type == "response.output_text.delta":
            self._text_delta(event, out)
        elif event_type == "response.function_call_arguments.delta":
            self._arguments_delta(event, out)
        elif event_type == "response.output_item.done":
            self._item_done(event.get("item"), out)
        elif event_type in _TERMINAL_SUCCESS:
            response = event.get("response")
            self._complete(response if isinstance(response, dict) else {}, out)
        elif event_type in _TERMINAL_FAILURE:
            self._fail(_event_error(event), out)
        return out

    def end_of_stream(self) -> list[dict[str, JsonValue]]:
        """Upstream ended without a terminal event."""
        if self.terminal:
            return []
        out: list[dict[str, JsonValue]] = []
        self._fail({"type": "server_error", "message": "Upstream stream ended before the response completed"}, out)
        return out

    # Upstream items -------------------------------------------------------------------------

    def _capture_id(self, response: JsonValue) -> None:
        if self._message_id is None and isinstance(response, dict):
            response_id = response.get("id")
            if isinstance(response_id, str) and response_id:
                self._message_id = "msg_" + response_id.removeprefix("resp_")

    def _item_added(self, item: JsonValue, out: list[dict[str, JsonValue]]) -> None:
        item_id = item.get("id") if isinstance(item, dict) else None
        if not isinstance(item, dict) or not isinstance(item_id, str):
            return
        record = self._record(item_id, item)
        if record.item_type == "function_call" and record.name is not None:
            self._start_tool(item_id, record, out)

    def _record(self, item_id: str, item: Mapping[str, JsonValue]) -> _Item:
        record = self._items.get(item_id)
        if record is None:
            item_type = item.get("type")
            record = self._items[item_id] = _Item(item_type=item_type if isinstance(item_type, str) else "")
        phase = item.get("phase")
        if isinstance(phase, str):
            record.phase = phase
        call_id = item.get("call_id")
        if isinstance(call_id, str) and call_id:
            record.call_id = call_id
        name = item.get("name")
        if isinstance(name, str) and name:
            record.name = name
        return record

    def _reasoning_delta(self, event: Mapping[str, JsonValue], out: list[dict[str, JsonValue]]) -> None:
        item_id, delta = event.get("item_id"), event.get("delta")
        if not isinstance(item_id, str) or not isinstance(delta, str) or not delta:
            return
        record = self._items.setdefault(item_id, _Item(item_type="reasoning"))
        part = event.get("summary_index", event.get("content_index"))
        part_index = part if isinstance(part, int) else 0
        self._open_block("thinking", item_id, out)
        if record.part_index is not None and part_index != record.part_index:
            delta = "\n\n" + delta
        record.part_index = part_index
        record.streamed = True
        out.append(self._delta({"type": "thinking_delta", "thinking": delta}))

    def _text_delta(self, event: Mapping[str, JsonValue], out: list[dict[str, JsonValue]]) -> None:
        item_id, delta = event.get("item_id"), event.get("delta")
        if not isinstance(item_id, str) or not isinstance(delta, str) or not delta:
            return
        record = self._items.setdefault(item_id, _Item(item_type="message"))
        record.streamed = True
        self._message_text(item_id, record, delta, out)

    def _message_text(self, item_id: str, record: _Item, text: str, out: list[dict[str, JsonValue]]) -> None:
        # A commentary-phase message is a preamble, not the answer (CLIProxyAPI 376015c3).
        if record.phase == "commentary":
            self._open_block("thinking", item_id, out)
            out.append(self._delta({"type": "thinking_delta", "thinking": text}))
        else:
            self._open_block("text", item_id, out)
            out.append(self._delta({"type": "text_delta", "text": text}))

    def _arguments_delta(self, event: Mapping[str, JsonValue], out: list[dict[str, JsonValue]]) -> None:
        item_id, delta = event.get("item_id"), event.get("delta")
        if not isinstance(item_id, str) or not isinstance(delta, str) or not delta:
            return
        record = self._items.setdefault(item_id, _Item(item_type="function_call"))
        if self._open == _OpenBlock("tool_use", item_id):
            record.streamed = True
            out.append(self._delta({"type": "input_json_delta", "partial_json": delta}))
        else:
            record.arguments.append(delta)

    def _item_done(self, item: JsonValue, out: list[dict[str, JsonValue]]) -> None:
        item_id = item.get("id") if isinstance(item, dict) else None
        if not isinstance(item, dict) or not isinstance(item_id, str):
            return
        record = self._record(item_id, item)
        if record.item_type == "reasoning":
            self._reasoning_done(item_id, item, record, out)
        elif record.item_type == "message":
            if not record.streamed and (text := _message_text(item)):
                self._message_text(item_id, record, text, out)
            self._close_item(item_id, out)
        elif record.item_type == "function_call":
            self._function_call_done(item_id, item, record, out)
        elif record.item_type == "web_search_call":
            self._web_search_done(item_id, item, out)

    def _reasoning_done(
        self, item_id: str, item: dict[str, JsonValue], record: _Item, out: list[dict[str, JsonValue]]
    ) -> None:
        encrypted = item.get("encrypted_content")
        if not record.streamed:
            summary = _reasoning_summary(item)
            if not summary and not isinstance(encrypted, str):
                return
            self._open_block("thinking", item_id, out)
            if summary:
                out.append(self._delta({"type": "thinking_delta", "thinking": summary}))
        if isinstance(encrypted, str) and encrypted and self._open == _OpenBlock("thinking", item_id):
            signature = seal_reasoning(
                ReasoningEnvelope(model=self._model, item_id=item_id, encrypted_content=encrypted),
                self._envelope_key,
            )
            out.append(self._delta({"type": "signature_delta", "signature": signature}))
        self._close_item(item_id, out)

    def _function_call_done(
        self, item_id: str, item: dict[str, JsonValue], record: _Item, out: list[dict[str, JsonValue]]
    ) -> None:
        if self._open != _OpenBlock("tool_use", item_id):
            self._start_tool(item_id, record, out)
        if not record.streamed:
            # The completed item's arguments are authoritative over deltas buffered before the
            # tool name was known (CLIProxyAPI 34639c3c).
            arguments = item.get("arguments")
            partial = arguments if isinstance(arguments, str) and arguments else "".join(record.arguments)
            if partial:
                out.append(self._delta({"type": "input_json_delta", "partial_json": partial}))
        self._close_item(item_id, out)

    def _start_tool(self, item_id: str, record: _Item, out: list[dict[str, JsonValue]]) -> None:
        self._close(out)
        name = record.name or ""
        self._tool_used = True
        self._open = _OpenBlock("tool_use", item_id)
        self.has_output = True
        out.append(
            {
                "type": "content_block_start",
                "index": self._index,
                "content_block": {
                    "type": "tool_use",
                    "id": record.call_id or item_id,
                    "name": self._tool_names.get(name, name),
                    "input": {},
                },
            }
        )

    def _web_search_done(self, item_id: str, item: dict[str, JsonValue], out: list[dict[str, JsonValue]]) -> None:
        self._close(out)
        self.has_output = True
        action = item.get("action")
        action = action if isinstance(action, dict) else {}
        query = action.get("query")
        out.append(
            {
                "type": "content_block_start",
                "index": self._index,
                "content_block": {"type": "server_tool_use", "id": item_id, "name": "web_search", "input": {}},
            }
        )
        if isinstance(query, str) and query:
            out.append(self._delta({"type": "input_json_delta", "partial_json": json.dumps({"query": query})}))
        out.append({"type": "content_block_stop", "index": self._index})
        self._index += 1
        out.append(
            {
                "type": "content_block_start",
                "index": self._index,
                "content_block": {
                    "type": "web_search_tool_result",
                    "tool_use_id": item_id,
                    "content": _web_search_results(action.get("sources")),
                },
            }
        )
        out.append({"type": "content_block_stop", "index": self._index})
        self._index += 1

    # Terminals ------------------------------------------------------------------------------

    def _complete(self, response: Mapping[str, JsonValue], out: list[dict[str, JsonValue]]) -> None:
        self._capture_id(response)
        self._close(out)
        self.terminal = True
        out.append(
            {
                "type": "message_delta",
                "delta": {"stop_reason": self._stop_reason(response), "stop_sequence": None},
                "usage": _usage(response.get("usage")),
            }
        )
        out.append({"type": "message_stop"})

    def _stop_reason(self, response: Mapping[str, JsonValue]) -> str:
        if self._tool_used:
            return "tool_use"
        details = response.get("incomplete_details")
        reason = details.get("reason") if isinstance(details, dict) else None
        if reason == "max_output_tokens":
            return "max_tokens"
        if reason == "content_filter":
            return "refusal"
        return "end_turn"

    def _fail(self, error: Mapping[str, JsonValue], out: list[dict[str, JsonValue]]) -> None:
        self.terminal = True
        self.error = anthropic_error(502, error)
        if not self.has_output:
            self.failure = self.error
            return
        self._close(out)
        out.append(self.error[1])

    # Blocks ---------------------------------------------------------------------------------

    def _open_block(self, kind: BlockKind, item_id: str, out: list[dict[str, JsonValue]]) -> None:
        if self._open == _OpenBlock(kind, item_id):
            return
        self._close(out)
        self._open = _OpenBlock(kind, item_id)
        self.has_output = True
        content_block: dict[str, JsonValue] = (
            {"type": "thinking", "thinking": "", "signature": ""}
            if kind == "thinking"
            else {"type": "text", "text": ""}
        )
        out.append({"type": "content_block_start", "index": self._index, "content_block": content_block})

    def _close_item(self, item_id: str, out: list[dict[str, JsonValue]]) -> None:
        if self._open is not None and self._open.item_id == item_id:
            self._close(out)

    def _close(self, out: list[dict[str, JsonValue]]) -> None:
        if self._open is None:
            return
        out.append({"type": "content_block_stop", "index": self._index})
        self._index += 1
        self._open = None

    def _delta(self, delta: dict[str, JsonValue]) -> dict[str, JsonValue]:
        return {"type": "content_block_delta", "index": self._index, "delta": delta}


def aggregate_message(start: dict[str, JsonValue], events: list[dict[str, JsonValue]]) -> dict[str, JsonValue]:
    """Fold a projected stream into one non-streaming Messages response."""
    message = start["message"]
    assert isinstance(message, dict)
    blocks: dict[int, dict[str, JsonValue]] = {}
    partial_json: dict[int, list[str]] = {}
    for event in events:
        event_type = event.get("type")
        index = event.get("index")
        if event_type == "content_block_start" and isinstance(index, int):
            block = event["content_block"]
            assert isinstance(block, dict)
            blocks[index] = dict(block)
        elif event_type == "content_block_delta" and isinstance(index, int):
            delta = event["delta"]
            assert isinstance(delta, dict)
            block = blocks[index]
            delta_type = delta.get("type")
            if delta_type == "text_delta":
                block["text"] = f"{block['text']}{delta['text']}"
            elif delta_type == "thinking_delta":
                block["thinking"] = f"{block['thinking']}{delta['thinking']}"
            elif delta_type == "signature_delta":
                block["signature"] = delta["signature"]
            elif delta_type == "input_json_delta":
                partial = delta["partial_json"]
                assert isinstance(partial, str)
                partial_json.setdefault(index, []).append(partial)
        elif event_type == "message_delta":
            delta = event["delta"]
            assert isinstance(delta, dict)
            message.update(delta)
            message["usage"] = event["usage"]
    for index, parts in partial_json.items():
        blocks[index]["input"] = json.loads("".join(parts))
    message["content"] = [blocks[index] for index in sorted(blocks)]
    return message


def _event_error(event: Mapping[str, JsonValue]) -> Mapping[str, JsonValue]:
    response = event.get("response")
    error = response.get("error") if isinstance(response, dict) else event.get("error")
    if isinstance(error, dict):
        return error
    return {"type": "server_error", "message": "Upstream response failed"}


def _message_text(item: Mapping[str, JsonValue]) -> str:
    content = item.get("content")
    if not isinstance(content, list):
        return ""
    texts: list[str] = []
    for part in content:
        if not isinstance(part, dict):
            continue
        text = part.get("text") if part.get("type") == "output_text" else part.get("refusal")
        if isinstance(text, str):
            texts.append(text)
    return "".join(texts)


def _reasoning_summary(item: Mapping[str, JsonValue]) -> str:
    parts = item.get("summary")
    if not isinstance(parts, list) or not parts:
        parts = item.get("content")
    if not isinstance(parts, list):
        return ""
    return "\n\n".join(
        text for part in parts if isinstance(part, dict) and isinstance(text := part.get("text"), str) and text
    )


def _web_search_results(sources: JsonValue) -> list[JsonValue]:
    if not isinstance(sources, list):
        return []
    results: list[JsonValue] = []
    for source in sources:
        if not isinstance(source, dict) or not isinstance(url := source.get("url"), str) or not url:
            continue
        title = source.get("title")
        results.append(
            {
                "type": "web_search_result",
                "title": title if isinstance(title, str) and title else url,
                "url": url,
                "page_age": None,
            }
        )
    return results


def _usage(usage: JsonValue) -> dict[str, JsonValue]:
    usage = usage if isinstance(usage, dict) else {}
    details = usage.get("input_tokens_details")
    details = details if isinstance(details, dict) else {}
    input_tokens = _count(usage.get("input_tokens"))
    cached = _count(details.get("cached_tokens"))
    cache_write = _count(details.get("cache_write_tokens")) or _count(details.get("cache_creation_tokens"))
    return {
        "input_tokens": max(0, input_tokens - cached - cache_write),
        "cache_read_input_tokens": cached,
        "cache_creation_input_tokens": cache_write,
        "output_tokens": _count(usage.get("output_tokens")),
    }


def _count(value: JsonValue) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else 0
