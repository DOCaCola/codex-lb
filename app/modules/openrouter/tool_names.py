"""Request-local OpenRouter wire identities; client history never stores aliases."""

from __future__ import annotations

import base64
import copy
import hashlib
import json
import re
from collections.abc import AsyncGenerator, AsyncIterator
from contextlib import aclosing
from dataclasses import dataclass, field
from typing import cast

from app.core.clients.proxy import MAX_SSE_EVENT_BYTES, StreamEventTooLargeError, _find_sse_separator
from app.core.openai.exceptions import ClientPayloadError
from app.core.types import JsonValue
from app.core.utils.sse import parse_sse_data_json

_SAFE_NAME = re.compile(r"[A-Za-z0-9_-]{1,64}\Z")
_PREFIX = "lbt_"


@dataclass(frozen=True)
class ToolIdentity:
    name: str
    namespace: str | None = None

    def alias(self) -> str:
        if self.namespace is None and _SAFE_NAME.fullmatch(self.name) and not self.name.startswith(_PREFIX):
            return self.name
        key = json.dumps([self.namespace, self.name], ensure_ascii=True, separators=(",", ":"))
        digest = base64.urlsafe_b64encode(hashlib.sha256(key.encode()).digest()).decode().rstrip("=")
        return _PREFIX + digest


@dataclass
class ToolNames:
    originals: dict[str, ToolIdentity] = field(default_factory=dict)
    fragments: dict[tuple[int, int], str] = field(default_factory=dict)
    echoed_fields: dict[str, JsonValue] = field(default_factory=dict)

    def rename(self, item: dict[str, JsonValue], namespace: str | None = None) -> None:
        name = item.get("name")
        if not isinstance(name, str):
            return
        explicit_namespace = item.get("namespace")
        identity = ToolIdentity(name, explicit_namespace if isinstance(explicit_namespace, str) else namespace)
        alias = identity.alias()
        owner = self.originals.get(alias)
        if owner is not None and owner != identity:
            raise ClientPayloadError("Tool wire identities collide", param="tools")
        if alias != name or identity.namespace is not None:
            self.originals[alias] = identity
        item["name"] = alias
        item.pop("namespace", None)

    def project(self, payload: dict[str, JsonValue], *, responses: bool) -> dict[str, JsonValue]:
        result = copy.deepcopy(payload)
        if responses:
            self.echoed_fields = {key: payload[key] for key in ("tools", "tool_choice") if key in payload}
        tools = result.get("tools")
        if isinstance(tools, list):
            projected: list[JsonValue] = []
            for tool in tools:
                if isinstance(tool, dict) and tool.get("type") == "namespace":
                    namespace, children = tool.get("name"), tool.get("tools")
                    if not isinstance(namespace, str) or not isinstance(children, list):
                        raise ClientPayloadError("Invalid tool namespace", param="tools")
                    for child in children:
                        if not isinstance(child, dict) or child.get("type") not in {"function", "custom"}:
                            raise ClientPayloadError("Unsupported namespaced tool", param="tools")
                        self.rename(child, namespace)
                        projected.append(child)
                else:
                    self.choice(tool, responses=responses)
                    projected.append(tool)
            result["tools"] = projected
        self.choice(result.get("tool_choice"), responses=responses)
        history = result.get("input" if responses else "messages")
        if isinstance(history, list):
            for item in history:
                if not isinstance(item, dict):
                    continue
                if responses and item.get("type") in {"function_call", "custom_tool_call"}:
                    self.rename(item)
                elif not responses:
                    calls = item.get("tool_calls")
                    if isinstance(calls, list):
                        for call in calls:
                            self.choice(call, responses=False)
                    if item.get("role") == "tool" and "name" in item:
                        self.rename(item)
        return result

    def choice(self, value: JsonValue, *, responses: bool) -> None:
        if not isinstance(value, dict):
            return
        if value.get("type") == "allowed_tools":
            tools = value.get("tools")
            if isinstance(tools, list):
                for tool in tools:
                    self.choice(tool, responses=responses)
        elif value.get("type") in {"function", "custom"}:
            target = value if responses else value.get("function")
            if isinstance(target, dict):
                self.rename(target)

    def restore_item(self, item: JsonValue) -> None:
        if not isinstance(item, dict) or item.get("type") not in {"function_call", "custom_tool_call"}:
            return
        name = item.get("name")
        identity = self.originals.get(name) if isinstance(name, str) else None
        if identity is not None:
            item["name"] = identity.name
            if identity.namespace is not None:
                item["namespace"] = identity.namespace

    def restore(self, payload: dict[str, JsonValue]) -> dict[str, JsonValue]:
        # Responses echoes request configuration on created/completed objects.
        # Return the client's declarations, not the flattened provider aliases.
        for key, original in self.echoed_fields.items():
            if key in payload:
                payload[key] = copy.deepcopy(original)
        self.restore_item(payload)
        self.restore_item(payload.get("item"))
        output = payload.get("output")
        if isinstance(output, list):
            for item in output:
                self.restore_item(item)
        response = payload.get("response")
        if isinstance(response, dict):
            self.restore(response)
        # Some Responses argument events carry the function name directly.
        kind = payload.get("type")
        if isinstance(kind, str) and kind.startswith(
            ("response.function_call_arguments.", "response.custom_tool_call_input.")
        ):
            name = payload.get("name")
            identity = self.originals.get(name) if isinstance(name, str) else None
            if identity is not None:
                payload["name"] = identity.name
                if identity.namespace is not None:
                    payload["namespace"] = identity.namespace
        choices = payload.get("choices")
        if isinstance(choices, list):
            for choice in choices:
                if not isinstance(choice, dict):
                    continue
                for field_name in ("message", "delta"):
                    message = choice.get(field_name)
                    calls = message.get("tool_calls") if isinstance(message, dict) else None
                    if not isinstance(calls, list):
                        continue
                    for call in calls:
                        if not isinstance(call, dict):
                            continue
                        function = call.get("function")
                        if not isinstance(function, dict):
                            continue
                        name = function.get("name")
                        if field_name == "delta":
                            key = (cast(int, choice.get("index", 0)), cast(int, call.get("index", 0)))
                            prior = self.fragments.pop(key, "")
                            combined = prior + (name if isinstance(name, str) else "")
                            identity = self.originals.get(combined)
                            if (
                                combined
                                and identity is None
                                and any(alias.startswith(combined) for alias in self.originals)
                                and not function.get("arguments")
                                and not choice.get("finish_reason")
                            ):
                                self.fragments[key] = combined
                                function.pop("name", None)
                            elif combined:
                                function["name"] = identity.name if identity else combined
                            continue
                        identity = self.originals.get(name) if isinstance(name, str) else None
                        if identity is not None:
                            function["name"] = identity.name
                if choice.get("finish_reason"):
                    index = choice.get("index", 0)
                    pending = [(key, name) for key, name in self.fragments.items() if key[0] == index]
                    if pending:
                        delta = choice.setdefault("delta", {})
                        if isinstance(delta, dict):
                            calls = delta.setdefault("tool_calls", [])
                            if isinstance(calls, list):
                                for key, name in pending:
                                    calls.append({"index": key[1], "function": {"name": name}})
                                    del self.fragments[key]
        return payload

    async def restore_stream(self, body: AsyncGenerator[bytes, None]) -> AsyncIterator[bytes]:
        if not self.originals:
            async with aclosing(body):
                async for chunk in body:
                    yield chunk
            return
        # Transport owns deadlines and cleanup; framing must not spawn read tasks.
        async with aclosing(body):
            async with aclosing(_frames(body)) as events:
                async for event in events:
                    payload = parse_sse_data_json(event)
                    if payload is None:
                        yield event.encode()
                        continue
                    original = json.dumps(payload, ensure_ascii=False)
                    restored = json.dumps(self.restore(payload), ensure_ascii=False)
                    if original == restored:
                        yield event.encode()
                        continue
                    # Preserve SSE id/retry/event/comments; replace only data.
                    lines = re.split(r"\r\n|\r|\n", event)
                    metadata = [line for line in lines if line and not line.startswith("data:") and line != "data"]
                    yield ("\n".join([*metadata, "data: " + restored]) + "\n\n").encode()


async def _frames(body: AsyncIterator[bytes]) -> AsyncGenerator[str, None]:
    buffer = bytearray()
    scanned = 0
    swallow_lf = False
    async for chunk in body:
        if not chunk:
            continue
        buffer.extend(chunk)
        if swallow_lf:
            swallow_lf = False
            if buffer[0] == 10:
                del buffer[0]
        while True:
            separator = _find_sse_separator(buffer, max(0, scanned - 4))
            if separator is None:
                scanned = len(buffer)
                if scanned > MAX_SSE_EVENT_BYTES:
                    raise StreamEventTooLargeError(scanned, MAX_SSE_EVENT_BYTES)
                break
            index, length = separator
            end = index + length
            if end > MAX_SSE_EVENT_BYTES:
                raise StreamEventTooLargeError(end, MAX_SSE_EVENT_BYTES)
            frame = bytes(buffer[:end])
            del buffer[:end]
            swallow_lf = frame.endswith(b"\r") and not buffer
            scanned = 0
            yield frame.decode("utf-8")
    if buffer:
        yield buffer.decode("utf-8")
