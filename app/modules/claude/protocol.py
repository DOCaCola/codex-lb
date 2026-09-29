"""Explicit Responses → Messages projection and reversible client tools."""

from __future__ import annotations

import base64
import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import cast

from pydantic import JsonValue

from app.core.openai.exceptions import ClientPayloadError
from app.modules.claude.capabilities import model_policy
from app.modules.claude.model_limits import default_output_tokens
from app.modules.claude.search import search_replay, search_tool
from app.modules.claude.tool_schema import ToolArguments, adapt_tool_schema


def invalid(message: str, param: str = "input") -> ClientPayloadError:
    return ClientPayloadError(message, param=param, code="unsupported_parameter")


@dataclass(frozen=True)
class ToolIdentity:
    name: str
    namespace: str | None
    custom: bool
    arguments: ToolArguments | None = None

    @property
    def wire_name(self) -> str:
        key = json.dumps([self.namespace, self.name, self.custom], separators=(",", ":"))
        return "tool_" + hashlib.sha256(key.encode()).hexdigest()[:40]


@dataclass(frozen=True)
class MessagesProjection:
    body: dict[str, JsonValue]
    tools: dict[str, ToolIdentity]
    search_enabled: bool = False


def _content(value: JsonValue) -> list[JsonValue]:
    if isinstance(value, str):
        return [{"type": "text", "text": value}]
    if not isinstance(value, list):
        raise invalid("Message content must be text or an array")
    result: list[JsonValue] = []
    for part in value:
        if not isinstance(part, dict):
            raise invalid("Invalid message content block")
        kind = part.get("type")
        if kind in ("input_text", "output_text", "text") and isinstance(part.get("text"), str):
            result.append({"type": "text", "text": part["text"]})
        elif kind == "input_image" and isinstance(part.get("image_url"), str):
            url = cast(str, part["image_url"])
            if url.startswith("data:"):
                prefix, separator, data = url.partition(",")
                if not separator or not prefix.endswith(";base64"):
                    raise invalid("Claude image data must be base64 encoded")
                media = prefix[5:-7]
                if media not in ("image/png", "image/jpeg", "image/gif", "image/webp"):
                    raise invalid("Unsupported Claude image media type")
                try:
                    base64.b64decode(data, validate=True)
                except ValueError as exc:
                    raise invalid("Invalid base64 image") from exc
                result.append({"type": "image", "source": {"type": "base64", "media_type": media, "data": data}})
            elif url.startswith("https://"):
                result.append({"type": "image", "source": {"type": "url", "url": url}})
            else:
                raise invalid("Claude images require HTTPS URLs or base64 data")
        else:
            raise invalid(f"Unsupported Claude input content type: {kind}")
    return result


def project_responses(
    payload: dict[str, JsonValue],
    *,
    max_output_tokens: int,
    restore_reasoning: Callable[[str], dict[str, JsonValue]] | None = None,
) -> MessagesProjection:
    if payload.get("previous_response_id") or payload.get("conversation"):
        raise invalid("Claude continuation must be expanded before protocol conversion", "previous_response_id")
    for field in ("audio", "modalities", "background"):
        if payload.get(field):
            raise invalid(f"Claude does not support Responses {field}", field)
    if payload.get("service_tier") not in (None, "auto", "default"):
        raise invalid("Claude OAuth cannot select an OpenAI billing service tier", "service_tier")
    if payload.get("truncation") not in (None, "disabled"):
        raise invalid("Claude does not support automatic Responses input truncation", "truncation")
    instructions = payload.get("instructions")
    system: list[JsonValue] = []
    if instructions is not None:
        if not isinstance(instructions, str):
            raise invalid("Claude instructions must be text", "instructions")
        if instructions:
            system.append({"type": "text", "text": instructions})
    tools: dict[str, ToolIdentity] = {}
    declarations: list[JsonValue] = []

    def declare(tool: JsonValue, namespace: str | None = None, *, param: str) -> None:
        if not isinstance(tool, dict):
            raise invalid("Invalid Claude tool declaration", "tools")
        kind = tool.get("type")
        if kind in ("web_search", "web_search_preview"):
            if namespace is not None:
                raise invalid("Hosted search cannot be namespaced", "tools")
            declaration = search_tool(tool)
            if declaration is not None:
                if any(isinstance(t, dict) and t.get("name") == "web_search" for t in declarations):
                    raise invalid("Duplicate web search declaration", "tools")
                declarations.append(declaration)
            return
        name = tool.get("name")
        if not isinstance(name, str) or not name:
            raise invalid("Tool name is required", "tools")
        if kind == "namespace":
            nested = tool.get("tools")
            if namespace is not None or not isinstance(nested, list):
                raise invalid("Invalid tool namespace", "tools")
            for index, child in enumerate(nested):
                declare(child, name, param=f"{param}.tools[{index}]")
            return
        if kind not in ("function", "custom"):
            raise invalid(f"Unsupported Claude tool type: {kind}", "tools")
        custom_format = tool.get("format")
        if (
            kind == "custom"
            and custom_format is not None
            and (not isinstance(custom_format, dict) or custom_format.get("type") != "text")
        ):
            raise invalid("Claude custom tools support text input, not grammar-constrained decoding", "tools")
        identity = ToolIdentity(name, namespace, kind == "custom")
        if identity.wire_name in tools:
            raise invalid("Duplicate tool identity", "tools")
        schema: JsonValue = (
            tool.get("parameters")
            if kind == "function"
            else {
                "type": "object",
                "properties": {"input": {"type": "string"}},
                "required": ["input"],
                "additionalProperties": False,
            }
        )
        if not isinstance(schema, dict):
            raise invalid(f"Tool '{name}' requires a JSON object schema", f"{param}.parameters")
        if kind == "function":
            schema, arguments = adapt_tool_schema(
                schema,
                tool_name=f"{namespace}.{name}" if namespace else name,
                param=f"{param}.parameters",
            )
            identity = replace(identity, arguments=arguments)
        tools[identity.wire_name] = identity
        declarations.append(
            {"name": identity.wire_name, "description": tool.get("description", ""), "input_schema": schema}
        )

    raw_tools = payload.get("tools", [])
    if not isinstance(raw_tools, list):
        raise invalid("Tools must be an array", "tools")
    for index, tool in enumerate(raw_tools):
        declare(tool, param=f"tools[{index}]")
    messages: list[JsonValue] = []

    def append(role: str, content: list[JsonValue]) -> None:
        if messages and isinstance(messages[-1], dict) and messages[-1].get("role") == role:
            previous = messages[-1]["content"]
            assert isinstance(previous, list)
            previous.extend(content)
        else:
            messages.append({"role": role, "content": content})

    items = payload.get("input", [])
    if isinstance(items, str):
        items = [{"role": "user", "content": items}]
    if not isinstance(items, list):
        raise invalid("Responses input must be text or an array")
    pending: set[str] = set()
    seen_calls: set[str] = set()
    search_items: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            raise invalid("Invalid Responses input item")
        kind = item.get("type", "message")
        if kind == "message":
            role = item.get("role")
            content = _content(item.get("content"))
            if role in ("system", "developer"):
                system.extend(content)
            elif role in ("user", "assistant"):
                if pending and role == "user":
                    raise invalid("Tool results are required before the next user message")
                append(role, content)
            else:
                raise invalid("Unsupported message role")
        elif kind in ("function_call", "custom_tool_call"):
            name, namespace, call_id = item.get("name"), item.get("namespace"), item.get("call_id")
            if (
                not isinstance(name, str)
                or not isinstance(call_id, str)
                or not call_id
                or (namespace is not None and not isinstance(namespace, str))
            ):
                raise invalid("Tool calls require a name and call_id")
            if call_id in seen_calls:
                raise invalid("Duplicate tool call_id")
            identity = ToolIdentity(name, namespace, kind == "custom_tool_call")
            identity = tools.setdefault(identity.wire_name, identity)
            if identity.custom:
                arguments: JsonValue = {"input": item.get("input")}
                if not isinstance(item.get("input"), str):
                    raise invalid("Custom tool input must be text")
            else:
                raw = item.get("arguments")
                if not isinstance(raw, str):
                    raise invalid("Function arguments must be JSON text")
                try:
                    arguments = json.loads(raw)
                except ValueError as exc:
                    raise invalid("Invalid function arguments") from exc
                if not isinstance(arguments, dict):
                    raise invalid("Function arguments must encode an object")
                if identity.arguments is not None:
                    arguments = identity.arguments.encode(arguments)
            append("assistant", [{"type": "tool_use", "id": call_id, "name": identity.wire_name, "input": arguments}])
            pending.add(call_id)
            seen_calls.add(call_id)
        elif kind in ("function_call_output", "custom_tool_call_output"):
            call_id = item.get("call_id")
            if not isinstance(call_id, str) or call_id not in pending:
                raise invalid("No matching Claude tool call for this output")
            append("user", [{"type": "tool_result", "tool_use_id": call_id, "content": _content(item.get("output"))}])
            pending.remove(call_id)
        elif kind == "web_search_call":
            item_id = item.get("id")
            if not isinstance(item_id, str) or item_id in search_items:
                raise invalid("Invalid Claude search history")
            search_items.add(item_id)
        elif kind == "reasoning":
            encrypted = item.get("encrypted_content")
            if encrypted:
                if not isinstance(encrypted, str) or restore_reasoning is None:
                    raise invalid("Claude signed reasoning must be restored by its account-bound continuation")
                restored = restore_reasoning(encrypted)
                if restored.get("type") == "web_search":
                    item_id, blocks = search_replay(restored)
                    if item_id not in search_items:
                        raise invalid("Claude search state has no matching search item")
                    search_items.remove(item_id)
                    append("assistant", blocks)
                else:
                    append("assistant", [restored])
                continue
            # Portable summaries are explicit text, not invented signed thinking.
            summary = item.get("summary", [])
            if not isinstance(summary, list):
                raise invalid("Invalid reasoning summary")
            for block in summary:
                if not isinstance(block, dict) or not isinstance(block.get("text"), str):
                    raise invalid("Invalid reasoning summary block")
                append("assistant", [{"type": "text", "text": block["text"]}])
        else:
            raise invalid(f"Unsupported Claude Responses item: {kind}")
    if search_items:
        raise invalid("Claude search history requires its account-bound opaque state; resend portable context")
    if pending:
        raise invalid("Claude tool calls require their outputs before continuing")
    if not messages:
        raise invalid("Claude requests require at least one message")
    limit = payload.get("max_output_tokens", default_output_tokens(max_output_tokens))
    if not isinstance(limit, int) or isinstance(limit, bool) or limit <= 0 or limit > max_output_tokens:
        raise invalid("Requested output limit exceeds the Claude model capability", "max_output_tokens")
    body: dict[str, JsonValue] = {
        "model": payload.get("model"),
        "messages": messages,
        "max_tokens": limit,
        "stream": payload.get("stream", False),
    }
    if "stop_sequences" in payload:
        stops = payload["stop_sequences"]
        if not isinstance(stops, list) or not stops or any(not isinstance(stop, str) or not stop for stop in stops):
            raise invalid("Claude stop sequences must be a non-empty array of non-empty strings", "stop")
        body["stop_sequences"] = stops
    if system:
        body["system"] = system
    if declarations:
        body["tools"] = declarations
    choice = payload.get("tool_choice", "auto")
    if choice in ("auto", "none", "required"):
        if declarations:
            body["tool_choice"] = {"type": "any" if choice == "required" else choice}
    elif isinstance(choice, dict):
        if choice.get("type") in ("web_search", "web_search_preview"):
            raise invalid("Forced hosted search is not supported for Claude", "tool_choice")
        identity = next(
            (
                identity
                for identity in tools.values()
                if identity.name == choice.get("name") and identity.namespace == choice.get("namespace")
            ),
            None,
        )
        if identity is None:
            raise invalid("Unknown tool choice", "tool_choice")
        body["tool_choice"] = {"type": "tool", "name": identity.wire_name}
    else:
        raise invalid("Unsupported tool choice", "tool_choice")
    if payload.get("parallel_tool_calls") is False and declarations:
        selected = body["tool_choice"]
        assert isinstance(selected, dict)
        selected["disable_parallel_tool_use"] = True
    reasoning = payload.get("reasoning")
    policy = model_policy(str(payload.get("model", "")))
    if isinstance(reasoning, dict) and reasoning.get("effort") not in (None, "none"):
        effort = reasoning.get("effort")
        if effort not in ("low", "medium", "high", "max"):
            raise invalid("Unsupported Claude reasoning effort", "reasoning")
        if policy is None or not policy.supports_reasoning:
            raise invalid("This Claude model has no configured reasoning policy", "reasoning")
        display = reasoning.get("display")
        if display not in (None, "summarized", "omitted"):
            raise invalid("Unsupported Claude thinking display", "reasoning")
        if policy.adaptive_reasoning:
            body["thinking"] = {"type": "adaptive"}
            if display == "summarized":
                body["thinking"]["display"] = "summarized"
            body["output_config"] = {"effort": effort}
        else:
            budget = {"low": 4096, "medium": 8192, "high": 16384, "max": 32000}[effort]
            if budget < 1024 or budget >= limit:
                raise invalid("Claude thinking budget must be below max_output_tokens", "max_output_tokens")
            body["thinking"] = {"type": "enabled", "budget_tokens": budget}
        if choice == "required" or isinstance(choice, dict):
            raise invalid("Claude thinking cannot be combined with a forced tool choice", "tool_choice")
    text = payload.get("text")
    if isinstance(text, dict):
        output_format = text.get("format")
        if isinstance(output_format, dict) and output_format.get("type") not in (None, "text"):
            if output_format.get("type") != "json_schema" or not isinstance(output_format.get("schema"), dict):
                raise invalid("Claude structured output requires a JSON schema", "text.format")
            if policy is None or not policy.structured_output:
                raise invalid("Claude structured output is not configured for this model", "text.format")
            config = body.setdefault("output_config", {})
            assert isinstance(config, dict)
            config["format"] = {"type": "json_schema", "schema": output_format["schema"]}
        verbosity = text.get("verbosity")
        if verbosity is not None:
            raise invalid(
                "Claude has no Responses verbosity control; specify verbosity in instructions", "text.verbosity"
            )
    for field in ("temperature", "top_p"):
        # An explicit null means "unset"; forwarding it would send ``null`` upstream.
        if payload.get(field) is not None:
            if "thinking" in body and (field == "top_p" or payload[field] != 1):
                raise invalid(f"Claude thinking cannot be combined with {field}", field)
            body[field] = payload[field]
    return MessagesProjection(
        body, tools, any(isinstance(t, dict) and t.get("type") == "web_search_20250305" for t in declarations)
    )
