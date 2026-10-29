"""Responses -> Cloud Code (Gemini) request projection with reversible client tools.

The wire image follows the native CLI capture (agy 1.4.10): system text in a
user-role systemInstruction, OpenAPI-dialect functionDeclarations, no toolConfig
for auto, functionResponse in role "model" for Gemini and "user" for
Claude-on-Antigravity, and thought parts replayed without signatures while the
step's first signature travels on its first functionCall.
"""

from __future__ import annotations

import base64
import json
import logging
import re
from dataclasses import dataclass, field, replace
from typing import cast

from pydantic import JsonValue

from app.core.openai.additional_tools import (
    ADDITIONAL_TOOLS,
    additional_tool_bundles,
    client_tool_namespace,
    collect_responses_tools,
)
from app.core.openai.exceptions import ClientPayloadError
from app.core.utils.request_id import get_request_id
from app.modules.antigravity.constants import SKIP_SIGNATURE
from app.modules.antigravity.opaque import PREFIX, AntigravityOpaqueState, ThoughtScope
from app.modules.antigravity.schemas import CatalogFamily
from app.modules.antigravity.tool_names import GoogleToolNames
from app.modules.antigravity.tool_schema import compile_tool_schema
from app.modules.claude.code_mode import code_mode_contract
from app.modules.claude.protocol import _custom_tool_input_schema as custom_tool_input_schema
from app.modules.claude.task_input import is_external_task_input
from app.modules.claude.tool_names import ToolIdentity

logger = logging.getLogger(__name__)

_IMAGE_TYPES = frozenset({"image/png", "image/jpeg", "image/webp", "image/heic", "image/heif"})
# Phrases that make Cloud Code answer a bare 429 despite remaining quota (CLIProxyAPI #5695, #5751);
# CLIProxyAPI PR #6280 obfuscates them in the system instruction by default.
SENSITIVE_WORDS = (
    "Claude Agent SDK",
    "system-conventions",
    "system_conventions",
    "system-directive",
    "system_directive",
    "RFC 2119",
)
_SENSITIVE = re.compile("|".join(re.escape(word) for word in sorted(SENSITIVE_WORDS, key=len, reverse=True)), re.I)
_ZERO_WIDTH_SPACE = "\u200b"


def invalid(message: str, param: str = "input") -> ClientPayloadError:
    return ClientPayloadError(message, param=param, code="unsupported_parameter")


def obfuscate(text: str) -> str:
    """Insert a zero-width space after the first character of each sensitive phrase (CLIProxyAPI cloak)."""
    return _SENSITIVE.sub(lambda match: match.group(0)[0] + _ZERO_WIDTH_SPACE + match.group(0)[1:], text)


@dataclass
class _Step:
    """One model content: its parts and the first thought signature this channel can verify."""

    parts: list[dict[str, JsonValue]] = field(default_factory=list)
    signature: str | None = None
    unsigned_thought: bool = False


@dataclass(frozen=True)
class GeminiProjection:
    request: dict[str, JsonValue]
    tools: GoogleToolNames
    # Steps whose calls carry a restored signature or the validator sentinel.
    restored: int = 0
    sentinels: int = 0
    # Claude-on-Antigravity cannot think through an open turn whose calls lost their signed thinking.
    thinking_disabled: bool = False


def _parts(value: JsonValue, *, param: str) -> list[dict[str, JsonValue]]:
    if isinstance(value, str):
        return [{"text": value}] if value else []
    if not isinstance(value, list):
        raise invalid("Message content must be text or an array", param)
    result: list[dict[str, JsonValue]] = []
    for part in value:
        if not isinstance(part, dict):
            raise invalid("Invalid message content block", param)
        kind = part.get("type")
        if kind in ("input_text", "output_text", "text") and isinstance(part.get("text"), str):
            if part["text"]:
                result.append({"text": part["text"]})
        elif kind == "input_image" and isinstance(part.get("image_url"), str):
            url = cast(str, part["image_url"])
            prefix, separator, data = url.partition(",")
            if not url.startswith("data:") or not separator or not prefix.endswith(";base64"):
                raise invalid("Antigravity images require base64 data URLs", param)
            media = prefix[5:-7]
            if media not in _IMAGE_TYPES:
                raise invalid("Unsupported Antigravity image media type", param)
            try:
                base64.b64decode(data, validate=True)
            except ValueError as exc:
                raise invalid("Invalid base64 image", param) from exc
            result.append({"inlineData": {"mimeType": media, "data": data}})
        else:
            raise invalid(f"Unsupported Antigravity input content type: {kind}", param)
    return result


def _output_text(value: JsonValue) -> tuple[str, list[dict[str, JsonValue]]]:
    """A tool output as its text and image siblings."""
    if isinstance(value, str):
        return value, []
    parts = _parts(value, param="input")
    text = "".join(str(part["text"]) for part in parts if "text" in part)
    return text, [part for part in parts if "inlineData" in part]


def project_responses(
    payload: dict[str, JsonValue],
    *,
    family: CatalogFamily,
    max_output_tokens: int,
    scope: ThoughtScope,
    opaque: AntigravityOpaqueState,
    restore_signatures: bool = True,
) -> GeminiProjection:
    """Translate a materialized Responses request; without restore_signatures every step is unsigned.

    Unsigned projection is the repair after Google rejects a restored signature: Gemini calls carry
    the validator sentinel and Claude-on-Antigravity drops the thinking (CLIProxyAPI reasoning replay).
    """
    if payload.get("previous_response_id") or payload.get("conversation"):
        raise invalid("Antigravity continuation must be expanded before protocol conversion", "previous_response_id")
    for name in ("audio", "modalities", "background"):
        if payload.get(name):
            raise invalid(f"Antigravity does not support Responses {name}", name)
    if payload.get("service_tier") not in (None, "auto", "default"):
        raise invalid("Antigravity cannot select an OpenAI billing service tier", "service_tier")
    if payload.get("truncation") not in (None, "disabled"):
        raise invalid("Antigravity does not support automatic Responses input truncation", "truncation")
    anthropic = family.anthropic_wire
    system: list[dict[str, JsonValue]] = []
    instructions = payload.get("instructions")
    if instructions is not None:
        if not isinstance(instructions, str):
            raise invalid("Antigravity instructions must be text", "instructions")
        if instructions.strip():
            system.append({"text": instructions})
    tools = GoogleToolNames()
    declarations: list[JsonValue] = []

    def declare(tool: JsonValue, namespace: str | None = None, *, param: str) -> None:
        if not isinstance(tool, dict):
            raise invalid("Invalid Antigravity tool declaration", "tools")
        kind = tool.get("type")
        if kind == "tool_search":
            if namespace is not None or tool.get("execution") != "client":
                raise invalid("Antigravity supports only client-executed tool search", f"{param}.execution")
            identity = ToolIdentity("tool_search", None, False, search=True)
            if identity in tools:
                raise invalid("Duplicate tool search declaration", param)
            schema = tool.get("parameters")
            if not isinstance(schema, dict):
                raise invalid("Tool search requires a JSON object schema", f"{param}.parameters")
            parameters, arguments = compile_tool_schema(schema, tool_name="tool_search", param=f"{param}.parameters")
            identity = replace(identity, arguments=arguments)
            declarations.append(_declaration(tools.add(identity), tool.get("description"), parameters))
            return
        name = tool.get("name")
        if not isinstance(name, str) or not name:
            raise invalid("Tool name is required", "tools")
        if kind == "namespace":
            nested = tool.get("tools")
            if namespace is not None or not isinstance(nested, list):
                raise invalid("Invalid tool namespace", "tools")
            member_namespace = client_tool_namespace(name)
            for index, child in enumerate(nested):
                if member_namespace is None and isinstance(child, dict) and child.get("type") == "namespace":
                    raise invalid("Invalid tool namespace", "tools")
                declare(child, member_namespace, param=f"{param}.tools[{index}]")
            return
        if kind not in ("function", "custom"):
            raise invalid(f"Unsupported Antigravity tool type: {kind}", "tools")
        identity = ToolIdentity(name, namespace, kind == "custom")
        if identity in tools:
            return
        qualified = f"{namespace}.{name}" if namespace else name
        if kind == "function":
            schema = tool.get("parameters", {"type": "object", "properties": {}})
            if not isinstance(schema, dict):
                raise invalid(f"Tool '{name}' requires a JSON object schema", f"{param}.parameters")
            parameters, arguments = compile_tool_schema(schema, tool_name=qualified, param=f"{param}.parameters")
            identity = replace(identity, arguments=arguments)
        else:
            parameters, _ = compile_tool_schema(
                custom_tool_input_schema(tool, param=param), tool_name=qualified, param=param
            )
        declarations.append(_declaration(tools.add(identity), tool.get("description"), parameters))

    raw_input = payload.get("input", [])
    if isinstance(raw_input, str):
        items: list[JsonValue] = [{"role": "user", "content": raw_input}]
    elif isinstance(raw_input, list):
        items = raw_input
    else:
        raise invalid("Responses input must be text or an array")
    raw_tools = payload.get("tools", [])
    if not isinstance(raw_tools, list):
        raise invalid("Tools must be an array", "tools")
    raw_tools = cast(list[JsonValue], collect_responses_tools(raw_tools, additional_tool_bundles(items)))
    for index, tool in enumerate(raw_tools):
        declare(tool, param=f"tools[{index}]")
    # Google has no deferred declarations: tools a search loaded are declared like any other.
    for index, item in enumerate(items):
        if isinstance(item, dict) and item.get("type") == "tool_search_output":
            loaded = item.get("tools")
            if not isinstance(loaded, list):
                raise invalid("Tool search output requires a tools array", f"input[{index}].tools")
            for position, tool in enumerate(loaded):
                declare(tool, param=f"input[{index}].tools[{position}]")
    contract = code_mode_contract(tools)
    if contract is not None:
        system.append({"text": contract})

    contents: list[dict[str, JsonValue]] = []
    step: _Step | None = None
    restored = sentinels = 0
    # Whether the open turn (since the last user message) holds calls without verifiable signed thinking.
    open_turn_unsigned = False

    def close_step() -> None:
        nonlocal step, restored, sentinels, open_turn_unsigned
        if step is None:
            return
        parts = step.parts
        calls = [part for part in parts if "functionCall" in part]
        if anthropic:
            # Anthropic thinking replays only with its own signature; unsigned thinking is dropped.
            thoughts = [part for part in parts if part.get("thought") is True]
            if step.signature is not None and thoughts:
                thoughts[0]["thoughtSignature"] = step.signature
                restored += 1
            else:
                parts = [part for part in parts if part.get("thought") is not True]
                open_turn_unsigned |= bool(calls)
        elif calls:
            if step.signature is not None:
                calls[0]["thoughtSignature"] = step.signature
                restored += 1
            else:
                calls[0]["thoughtSignature"] = SKIP_SIGNATURE
                sentinels += 1
        if parts:
            contents.append({"role": "model", "parts": cast(JsonValue, parts)})
        step = None

    def model_parts() -> _Step:
        nonlocal step
        if step is None:
            step = _Step()
        return step

    def append_user(parts: list[dict[str, JsonValue]]) -> None:
        close_step()
        if not parts:
            return
        last = contents[-1] if contents else None
        if last is not None and last.get("role") == "user" and not _has_responses(last):
            cast(list[JsonValue], last["parts"]).extend(parts)
        else:
            contents.append({"role": "user", "parts": cast(JsonValue, parts)})

    call_ids = {
        call_id
        for item in items
        if isinstance(item, dict)
        and item.get("type") in ("function_call", "custom_tool_call", "tool_search_call")
        and isinstance(call_id := item.get("call_id"), str)
    }
    calls: dict[str, str] = {}
    pending: set[str] = set()
    answered: set[str] = set()
    pending_system: list[dict[str, JsonValue]] = []
    responses: list[dict[str, JsonValue]] = []
    response_images: list[dict[str, JsonValue]] = []

    def flush_responses() -> None:
        if not responses:
            return
        close_step()
        contents.append(
            {"role": "user" if anthropic else "model", "parts": cast(JsonValue, [*responses, *response_images])}
        )
        responses.clear()
        response_images.clear()

    def place_system() -> None:
        if pending_system:
            append_user([{"text": "<system-reminder>"}, *pending_system, {"text": "</system-reminder>"}])
            pending_system.clear()

    for index, item in enumerate(items):
        param = f"input[{index}]"
        if not isinstance(item, dict):
            raise invalid("Invalid Responses input item", param)
        kind = item.get("type", "message")
        if kind == ADDITIONAL_TOOLS:
            continue
        if kind != "function_call_output" and kind != "custom_tool_call_output" and kind != "tool_search_output":
            flush_responses()
        if kind == "message":
            role = item.get("role")
            parts = _parts(item.get("content"), param=param)
            if role in ("system", "developer"):
                (pending_system if contents or step is not None else system).extend(parts)
            elif role == "user":
                if pending:
                    raise invalid("Tool results are required before the next user message", param)
                place_system()
                append_user(parts)
                open_turn_unsigned = False
            elif role == "assistant":
                place_system()
                model_parts().parts.extend(parts)
            else:
                raise invalid("Unsupported message role", param)
        elif kind in ("function_call", "custom_tool_call", "tool_search_call"):
            call_id = item.get("call_id")
            if not isinstance(call_id, str) or not call_id:
                raise invalid("Tool calls require a call_id", param)
            if call_id in calls:
                raise invalid("Duplicate tool call_id", param)
            if kind == "tool_search_call":
                identity = tools.identity(ToolIdentity("tool_search", None, False, search=True))
                arguments = item.get("arguments")
                if not isinstance(arguments, dict):
                    raise invalid("Tool search calls require object arguments", param)
            else:
                name, namespace = item.get("name"), item.get("namespace")
                if not isinstance(name, str) or (namespace is not None and not isinstance(namespace, str)):
                    raise invalid("Tool calls require a name", param)
                identity = tools.identity(
                    ToolIdentity(name, client_tool_namespace(namespace), kind == "custom_tool_call")
                )
                if identity.custom:
                    if not isinstance(item.get("input"), str):
                        raise invalid("Custom tool input must be text", param)
                    arguments = {"input": item["input"]}
                else:
                    raw = item.get("arguments")
                    try:
                        arguments = json.loads(raw) if isinstance(raw, str) else None
                    except ValueError as exc:
                        raise invalid("Invalid function arguments", param) from exc
                    if not isinstance(arguments, dict):
                        raise invalid("Function arguments must encode an object", param)
            if identity.arguments is not None:
                arguments = identity.arguments.encode(cast(dict[str, JsonValue], arguments))
            wire = tools.wire_name(identity)
            model_parts().parts.append({"functionCall": {"id": call_id, "name": wire, "args": arguments}})
            calls[call_id] = wire
            pending.add(call_id)
        elif kind in ("function_call_output", "custom_tool_call_output", "tool_search_output"):
            if kind != "tool_search_output" and is_external_task_input(item):
                if pending:
                    raise invalid("Tool results are required before the next task input", param)
                append_user(_parts(item.get("output"), param=param))
                continue
            call_id = item.get("call_id")
            if not isinstance(call_id, str) or not call_id.strip():
                raise invalid("Tool output requires a call_id", param)
            if kind == "tool_search_output":
                loaded = item.get("tools")
                names = [
                    str(tool.get("name"))
                    for tool in cast(list[JsonValue], loaded)
                    if isinstance(tool, dict) and isinstance(tool.get("name"), str)
                ]
                text, images = ("Loaded tools: " + ", ".join(names) if names else "No matching tools found."), []
            else:
                text, images = _output_text(item.get("output"))
            if call_id in pending:
                close_step()
                responses.append(
                    {"functionResponse": {"id": call_id, "name": calls[call_id], "response": {"output": text}}}
                )
                response_images.extend(images)
                pending.remove(call_id)
                answered.add(call_id)
            elif call_id in answered and kind == "custom_tool_call_output":
                # A code-mode notify() output after its exec call's own result.
                flush_responses()
                append_user([{"text": f"[Later exec output: call_id={call_id}]"}, {"text": text}, *images])
            elif call_id in call_ids and call_id not in calls:
                raise invalid("Tool output precedes its call", param)
            elif call_id in answered:
                raise invalid("Duplicate tool output", param)
            elif pending:
                raise invalid("Tool results are required before unrelated tool output", param)
            else:
                # Imported or delegated history: output without a call here is context, not a tool cycle.
                append_user([{"text": f"[Standalone {kind}: call_id={call_id}]"}, {"text": text}, *images])
        elif kind == "reasoning":
            token = item.get("encrypted_content")
            if not isinstance(token, str) or not token.startswith(PREFIX):
                # Foreign reasoning was projected to portable text before translation.
                continue
            thought = opaque.open(token, client_scope=scope.client_scope, param=param)
            current = model_parts()
            if thought.text:
                current.parts.append({"text": thought.text, "thought": True})
            if restore_signatures and scope.owns(thought) and thought.signature is not None:
                current.signature = current.signature or thought.signature
        elif kind == "web_search_call":
            # Hosted search ran on another provider; its findings are in the surrounding messages.
            continue
        else:
            raise invalid(f"Unsupported Antigravity Responses item: {kind}", param)
    flush_responses()
    if pending:
        raise invalid("Antigravity tool calls require their outputs before continuing")
    close_step()
    place_system()
    if not contents:
        raise invalid("Antigravity requests require at least one message")
    if contents[0].get("role") == "model" and not _has_responses(contents[0]):
        # Gemini rejects history that opens with a model call (opencodex).
        contents.insert(0, {"role": "user", "parts": [{"text": "(continue)"}]})
    if contents[-1].get("role") == "model" and not _has_responses(contents[-1]):
        contents.append({"role": "user", "parts": [{"text": "(continue)"}]})
        logger.info("antigravity_continuation_projected request_id=%s reason=model_tail", get_request_id())
    request: dict[str, JsonValue] = {"contents": cast(JsonValue, contents)}
    if system:
        request["systemInstruction"] = {
            "role": "user",
            "parts": [{"text": obfuscate(str(part["text"]))} for part in system],
        }
    choice = payload.get("tool_choice", "auto")
    if isinstance(choice, dict) and choice.get("type") in ("auto", "none", "required") and len(choice) == 1:
        choice = choice["type"]
    if declarations and choice != "none":
        request["tools"] = [{"functionDeclarations": declarations}]
        if choice == "required":
            request["toolConfig"] = {"functionCallingConfig": {"mode": "ANY"}}
        elif isinstance(choice, dict) and choice.get("type") in ("function", "custom"):
            identity = next(
                (
                    identity
                    for identity in tools.by_wire.values()
                    if identity.name == choice.get("name") and identity.namespace == choice.get("namespace")
                ),
                None,
            )
            if identity is None:
                raise invalid("Unknown tool choice", "tool_choice")
            request["toolConfig"] = {
                "functionCallingConfig": {"mode": "ANY", "allowedFunctionNames": [tools.wire_name(identity)]}
            }
        elif choice != "auto":
            raise invalid("Unsupported tool choice", "tool_choice")
        if payload.get("parallel_tool_calls") is False:
            raise invalid("Antigravity cannot guarantee serial tool calls", "parallel_tool_calls")
    limit = payload.get("max_output_tokens", max_output_tokens)
    if not isinstance(limit, int) or isinstance(limit, bool) or limit <= 0 or limit > max_output_tokens:
        raise invalid("Requested output limit exceeds the Antigravity model capability", "max_output_tokens")
    generation: dict[str, JsonValue] = {"maxOutputTokens": limit}
    thinking_disabled = anthropic and open_turn_unsigned
    if family.supports_thinking and not thinking_disabled:
        generation["thinkingConfig"] = {"includeThoughts": True, "thinkingBudget": -1}
    if thinking_disabled:
        logger.info("antigravity_thinking_projection request_id=%s reason=unsigned_open_turn", get_request_id())
    for source, target in (("temperature", "temperature"), ("top_p", "topP")):
        if payload.get(source) is not None:
            generation[target] = payload[source]
    stops = payload.get("stop_sequences")
    if stops is not None:
        if not isinstance(stops, list) or not all(isinstance(stop, str) and stop for stop in stops):
            raise invalid("Stop sequences must be non-empty strings", "stop")
        generation["stopSequences"] = stops
    text = payload.get("text")
    if isinstance(text, dict):
        output_format = text.get("format")
        if isinstance(output_format, dict) and output_format.get("type") not in (None, "text"):
            if output_format.get("type") != "json_schema" or not isinstance(output_format.get("schema"), dict):
                raise invalid("Antigravity structured output requires a JSON schema", "text.format")
            generation["responseMimeType"] = "application/json"
            generation["responseJsonSchema"] = output_format["schema"]
        if text.get("verbosity") is not None:
            raise invalid("Antigravity has no verbosity control; specify verbosity in instructions", "text.verbosity")
    request["generationConfig"] = generation
    return GeminiProjection(request, tools, restored, sentinels, thinking_disabled)


def _declaration(name: str, description: JsonValue, parameters: dict[str, JsonValue] | None) -> JsonValue:
    declaration: dict[str, JsonValue] = {
        "name": name,
        "description": description if isinstance(description, str) else "",
    }
    if parameters is not None:
        declaration["parameters"] = parameters
    return declaration


def _has_responses(content: dict[str, JsonValue]) -> bool:
    parts = content.get("parts")
    return isinstance(parts, list) and any(isinstance(part, dict) and "functionResponse" in part for part in parts)
