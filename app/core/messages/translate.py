"""Translate an Anthropic Messages request into one Responses request.

The mapping follows CLIProxyAPI's Codex/Claude translator, including its production fixes:
64-character tool name and call ID limits, JSON Schema dialect cleanup, Claude Code billing
attribution removal, PDF documents, hosted web search, and system messages placed after
pending tool outputs. Reasoning continuity uses the signed envelope in `envelope`.

The requested effort is projected onto the target model's supported levels like CLIProxyAPI's cross-family
thinking validation (`internal/thinking/validate.go`): Claude effort values and disabled thinking do not map
onto every OpenAI model's levels, so the nearest supported level is sent, the lower one on a tie.
"""

from __future__ import annotations

import hashlib
import json
import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from app.core.messages.envelope import is_proxy_signature, open_reasoning
from app.core.messages.errors import MessagesRequestError
from app.core.types import JsonValue

logger = logging.getLogger(__name__)

_NAME_LIMIT = 64
_BILLING_ATTRIBUTION_PREFIX = "x-anthropic-billing-header:"
_WEB_SEARCH_TOOL_TYPES = frozenset({"web_search_20250305", "web_search_20260209"})
_FUNCTION_TOOL_TYPES = frozenset({"custom"})
_UNSUPPORTED_FIELDS = ("top_k", "container")
_SCHEMA_DIALECT_KEYS = ("$schema", "$id")
_SCHEMA_MAP_KEYWORDS = ("properties", "$defs", "definitions", "dependentSchemas")
_SCHEMA_VALUE_KEYWORDS = (
    "items",
    "prefixItems",
    "additionalProperties",
    "anyOf",
    "allOf",
    "oneOf",
    "not",
    "if",
    "then",
    "else",
    "contains",
    "propertyNames",
    "unevaluatedItems",
    "unevaluatedProperties",
)
_BUDGET_EFFORTS = ((512, "minimal"), (1024, "low"), (8192, "medium"), (24576, "high"))
# Wire efforts from lowest to highest; `none` is the bottom rung, so disabled thinking projects to the lowest level.
_EFFORT_ORDER = ("none", "minimal", "low", "medium", "high", "xhigh", "max")


@dataclass(frozen=True, slots=True)
class TranslatedMessages:
    payload: dict[str, JsonValue]
    # Upstream tool name -> client tool name, for names shortened to the Responses limit.
    tool_names: dict[str, str]
    stream: bool


@dataclass(frozen=True, slots=True)
class MessagesIdentity:
    session_id: str | None
    agent_id: str


def messages_identity(body: Mapping[str, JsonValue], headers: Mapping[str, str]) -> MessagesIdentity:
    """Claude Code's session and agent; the header and metadata session must agree."""
    values = {key.lower(): value.strip() for key, value in headers.items()}
    header_session = values.get("x-claude-code-session-id") or None
    metadata_session = _metadata_session(body.get("metadata"))
    if header_session and metadata_session and header_session != metadata_session:
        raise MessagesRequestError("Claude Code session header and metadata disagree")
    return MessagesIdentity(
        session_id=header_session or metadata_session,
        agent_id=values.get("x-claude-code-agent-id") or "main",
    )


def translate_messages_request(
    body: Mapping[str, JsonValue],
    *,
    model: str,
    fast: bool,
    identity: MessagesIdentity,
    envelope_key: bytes,
    reasoning_levels: Sequence[str],
) -> TranslatedMessages:
    """Translate a Messages request; `fast` is a Fast selector chosen through the model alias.

    `reasoning_levels` are the efforts the target model's catalog entry supports; empty leaves effort unprojected.
    """
    _reject_unsupported_fields(body, model)
    tools_value = body.get("tools") or []
    if not isinstance(tools_value, list):
        raise MessagesRequestError("tools must be an array")
    tools, web_search_names, has_web_search = _translate_tools(tools_value, model)
    instructions = _instructions(body.get("system"))
    input_items = _MessagesInput(model=model, envelope_key=envelope_key).translate(body.get("messages"))

    payload: dict[str, JsonValue] = {
        "model": model,
        "instructions": instructions,
        "input": input_items,
        "store": False,
        "stream": True,
        "include": ["reasoning.encrypted_content", *(["web_search_call.action.sources"] if has_web_search else [])],
        "parallel_tool_calls": not _disable_parallel_tool_use(body.get("tool_choice")),
        "prompt_cache_key": _prompt_cache_key(model, identity, instructions, tools),
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = _tool_choice(body.get("tool_choice"), web_search_names)
    reasoning = _reasoning(body, model=model, reasoning_levels=reasoning_levels)
    if reasoning:
        payload["reasoning"] = reasoning
    max_tokens = body.get("max_tokens")
    if isinstance(max_tokens, int) and not isinstance(max_tokens, bool):
        payload["max_output_tokens"] = max_tokens
    for field in ("temperature", "top_p"):
        value = body.get(field)
        if value is not None:
            payload[field] = value
    text_format = _text_format(body.get("output_config"))
    if text_format is not None:
        payload["text"] = {"format": text_format}
    if fast or body.get("speed") == "fast":
        payload["service_tier"] = "priority"
    return TranslatedMessages(
        payload=payload,
        tool_names={alias: name for name in _declared_tool_names(tools_value) if (alias := tool_alias(name)) != name},
        stream=body.get("stream") is True,
    )


def tool_alias(value: str) -> str:
    """Deterministic alias for tool names and call IDs above the Responses 64-character limit."""
    if len(value) <= _NAME_LIMIT:
        return value
    suffix = "_" + hashlib.sha256(value.encode()).hexdigest()[:16]
    return value[: _NAME_LIMIT - len(suffix)] + suffix


def _reject_unsupported_fields(body: Mapping[str, JsonValue], model: str) -> None:
    if body.get("stop_sequences"):
        raise MessagesRequestError(f"stop_sequences is not supported for model '{model}'")
    if body.get("mcp_servers"):
        raise MessagesRequestError(f"mcp_servers is not supported for model '{model}'")
    for field in _UNSUPPORTED_FIELDS:
        if body.get(field) is not None:
            raise MessagesRequestError(f"{field} is not supported for model '{model}'")


def _metadata_session(metadata: JsonValue) -> str | None:
    if not isinstance(metadata, dict):
        return None
    user_id = metadata.get("user_id")
    if not isinstance(user_id, str):
        return None
    try:
        parsed = json.loads(user_id)
    except ValueError:
        return None
    session_id = parsed.get("session_id") if isinstance(parsed, dict) else None
    return session_id if isinstance(session_id, str) and session_id else None


def _prompt_cache_key(model: str, identity: MessagesIdentity, instructions: str, tools: list[JsonValue]) -> str:
    # Session and agent scope the cache lineage (CLIProxyAPI); without a session, requests
    # sharing model, instructions and tools form one cohort (opencodex).
    if identity.session_id is not None:
        material: JsonValue = ["messages-session-v1", model, identity.session_id, identity.agent_id]
    else:
        material = ["messages-cohort-v1", model, instructions, tools]
    return hashlib.sha256(json.dumps(material, separators=(",", ":")).encode()).hexdigest()


def _instructions(system: JsonValue) -> str:
    if system is None:
        return ""
    if isinstance(system, str):
        texts = [system]
    elif isinstance(system, list):
        texts = []
        for block in system:
            text = block.get("text") if isinstance(block, dict) and block.get("type") == "text" else None
            if not isinstance(text, str):
                raise MessagesRequestError("system must be text or an array of text blocks")
            texts.append(text)
    else:
        raise MessagesRequestError("system must be text or an array of text blocks")
    return "\n\n".join(text for text in texts if text and not text.startswith(_BILLING_ATTRIBUTION_PREFIX))


def _declared_tool_names(tools: list[JsonValue]) -> list[str]:
    return [
        name
        for tool in tools
        if isinstance(tool, dict)
        and isinstance(name := tool.get("name"), str)
        and tool.get("type") not in _WEB_SEARCH_TOOL_TYPES
    ]


def _translate_tools(tools: list[JsonValue], model: str) -> tuple[list[JsonValue], set[str], bool]:
    translated: list[JsonValue] = []
    web_search_names: set[str] = set()
    for tool in tools:
        if not isinstance(tool, dict):
            raise MessagesRequestError("Each tool must be an object")
        tool_type = tool.get("type")
        name = tool.get("name")
        if tool_type in _WEB_SEARCH_TOOL_TYPES:
            if isinstance(name, str):
                web_search_names.add(name)
            web_search: dict[str, JsonValue] = {"type": "web_search"}
            allowed_domains = tool.get("allowed_domains")
            if isinstance(allowed_domains, list):
                web_search["filters"] = {"allowed_domains": allowed_domains}
            user_location = tool.get("user_location")
            if isinstance(user_location, dict):
                web_search["user_location"] = user_location
            translated.append(web_search)
            continue
        if tool_type is not None and tool_type not in _FUNCTION_TOOL_TYPES:
            raise MessagesRequestError(f"Tool type '{tool_type}' is not supported for model '{model}'")
        if not isinstance(name, str) or not name:
            raise MessagesRequestError("Each tool requires a name")
        function: dict[str, JsonValue] = {
            "type": "function",
            "name": tool_alias(name),
            "parameters": _tool_parameters(tool.get("input_schema")),
            "strict": False,
        }
        description = tool.get("description")
        if isinstance(description, str) and description:
            function["description"] = description
        translated.append(function)
    return translated, web_search_names, bool(web_search_names)


def _tool_parameters(schema: JsonValue) -> dict[str, JsonValue]:
    if not isinstance(schema, dict):
        return {"type": "object", "properties": {}}
    parameters = _clean_schema(schema)
    assert isinstance(parameters, dict)
    schema_type = parameters.get("type")
    if schema_type is None:
        parameters["type"] = "object"
    if (
        parameters["type"] == "object" or (isinstance(schema_type, list) and "object" in schema_type)
    ) and not isinstance(parameters.get("properties"), dict):
        parameters["properties"] = {}
    return parameters


def _clean_schema(schema: JsonValue) -> JsonValue:
    """Remove JSON Schema dialect keywords and regexes with Unicode property escapes."""
    if isinstance(schema, list):
        return [_clean_schema(item) for item in schema]
    if not isinstance(schema, dict):
        return schema
    cleaned: dict[str, JsonValue] = {}
    for key, value in schema.items():
        if key in _SCHEMA_DIALECT_KEYS:
            continue
        if key == "pattern" and isinstance(value, str) and _has_unicode_property_escape(value):
            continue
        if key == "patternProperties" and isinstance(value, dict):
            cleaned[key] = {
                pattern: _clean_schema(sub)
                for pattern, sub in value.items()
                if not _has_unicode_property_escape(pattern)
            }
        elif key in _SCHEMA_MAP_KEYWORDS and isinstance(value, dict):
            cleaned[key] = {name: _clean_schema(sub) for name, sub in value.items()}
        elif key in _SCHEMA_VALUE_KEYWORDS:
            cleaned[key] = _clean_schema(value)
        else:
            cleaned[key] = value
    return cleaned


def _has_unicode_property_escape(pattern: str) -> bool:
    return "\\p{" in pattern or "\\P{" in pattern


def _disable_parallel_tool_use(tool_choice: JsonValue) -> bool:
    return isinstance(tool_choice, dict) and tool_choice.get("disable_parallel_tool_use") is True


def _tool_choice(tool_choice: JsonValue, web_search_names: set[str]) -> JsonValue:
    if not isinstance(tool_choice, dict):
        return "auto"
    choice_type = tool_choice.get("type")
    if choice_type == "any":
        return "required"
    if choice_type == "none":
        return "none"
    if choice_type == "tool":
        name = tool_choice.get("name")
        if not isinstance(name, str) or not name:
            raise MessagesRequestError("tool_choice of type 'tool' requires a name")
        if name in web_search_names:
            return {"type": "web_search"}
        return {"type": "function", "name": tool_alias(name)}
    return "auto"


def _reasoning(body: Mapping[str, JsonValue], *, model: str, reasoning_levels: Sequence[str]) -> dict[str, JsonValue]:
    thinking = body.get("thinking")
    thinking_type = thinking.get("type") if isinstance(thinking, dict) else None
    output_config = body.get("output_config")
    effort = output_config.get("effort") if isinstance(output_config, dict) else None
    reasoning: dict[str, JsonValue] = {}
    if isinstance(effort, str) and effort:
        reasoning["effort"] = effort.strip().lower()
    elif thinking_type == "disabled":
        reasoning["effort"] = "none"
    elif thinking_type == "enabled" and isinstance(thinking, dict):
        budget = thinking.get("budget_tokens")
        if isinstance(budget, int) and not isinstance(budget, bool):
            reasoning["effort"] = next((name for limit, name in _BUDGET_EFFORTS if budget <= limit), "xhigh")
    display = thinking.get("display") if isinstance(thinking, dict) else None
    if thinking_type != "disabled" and display != "omitted":
        reasoning["summary"] = "auto"
    effort = reasoning.get("effort")
    if isinstance(effort, str):
        projected = _project_effort(effort, reasoning_levels)
        if projected != effort:
            reasoning["effort"] = projected
            logger.info(
                "messages_reasoning_effort_projected model=%s requested_effort=%s projected_effort=%s",
                model,
                effort,
                projected,
            )
    return reasoning


def _project_effort(effort: str, reasoning_levels: Sequence[str]) -> str:
    """The supported level nearest to `effort`, the lower one on a tie; unknown efforts pass through."""
    supported = [_EFFORT_ORDER.index(level) for level in reasoning_levels if level in _EFFORT_ORDER]
    if not supported or effort not in _EFFORT_ORDER or effort in reasoning_levels:
        return effort
    requested = _EFFORT_ORDER.index(effort)
    return _EFFORT_ORDER[min(supported, key=lambda rank: (abs(rank - requested), rank))]


def _text_format(output_config: JsonValue) -> dict[str, JsonValue] | None:
    if not isinstance(output_config, dict):
        return None
    format_value = output_config.get("format")
    if not isinstance(format_value, dict) or format_value.get("type") != "json_schema":
        return None
    schema = format_value.get("schema")
    if not isinstance(schema, dict):
        raise MessagesRequestError("output_config.format.schema must be an object")
    name = format_value.get("name")
    # Strict output requires every property to be required; downgrade instead of sending an
    # unsatisfiable strict schema (CLIProxyAPI aa365277).
    strict = format_value.get("strict") is not False and not _schema_misses_required(schema)
    return {
        "type": "json_schema",
        "name": name if isinstance(name, str) and name else "output",
        "schema": schema,
        "strict": strict,
    }


def _schema_misses_required(schema: JsonValue) -> bool:
    if isinstance(schema, list):
        return any(_schema_misses_required(item) for item in schema)
    if not isinstance(schema, dict):
        return False
    properties = schema.get("properties")
    if isinstance(properties, dict) and properties:
        required = schema.get("required")
        required_names = {item for item in required if isinstance(item, str)} if isinstance(required, list) else set()
        if any(name not in required_names for name in properties):
            return True
    for keyword in _SCHEMA_MAP_KEYWORDS:
        children = schema.get(keyword)
        if isinstance(children, dict) and any(_schema_misses_required(child) for child in children.values()):
            return True
    return any(_schema_misses_required(schema.get(keyword)) for keyword in _SCHEMA_VALUE_KEYWORDS)


class _MessagesInput:
    def __init__(self, *, model: str, envelope_key: bytes) -> None:
        self._model = model
        self._envelope_key = envelope_key
        self._items: list[JsonValue] = []
        self._parts: list[JsonValue] = []
        self._role = "user"
        self._pending_tool_calls = False
        self._deferred_developer: list[JsonValue] = []

    def translate(self, messages: JsonValue) -> list[JsonValue]:
        if not isinstance(messages, list):
            raise MessagesRequestError("messages must be an array")
        for message in messages:
            if not isinstance(message, dict):
                raise MessagesRequestError("Each message must be an object")
            role = message.get("role")
            if role == "system":
                self._system_message(message.get("content"))
                continue
            if role not in ("user", "assistant"):
                raise MessagesRequestError(f"Unsupported message role '{role}'")
            self._role = role
            self._message(message.get("content"))
        self._flush_deferred()
        return self._items

    def _system_message(self, content: JsonValue) -> None:
        # Responses requires each function call to be followed by its output, so a system
        # message between a tool call and its result waits for the outputs (CLIProxyAPI 9fdc4605).
        text = _instructions(content)
        if not text:
            return
        item: dict[str, JsonValue] = {
            "type": "message",
            "role": "developer",
            "content": [{"type": "input_text", "text": text}],
        }
        if self._pending_tool_calls:
            self._deferred_developer.append(item)
        else:
            self._items.append(item)

    def _message(self, content: JsonValue) -> None:
        if isinstance(content, str):
            self._resolve_tool_calls()
            self._text(content)
        elif isinstance(content, list):
            for block in content:
                if not isinstance(block, dict):
                    raise MessagesRequestError("Each content block must be an object")
                self._block(block)
        else:
            raise MessagesRequestError("Message content must be text or an array of content blocks")
        self._flush_parts()
        if self._role == "user":
            self._resolve_tool_calls()

    def _block(self, block: dict[str, JsonValue]) -> None:
        block_type = block.get("type")
        if block_type == "tool_result" and self._role == "user":
            self._flush_parts()
            self._items.append(self._tool_result(block))
            return
        if block_type == "tool_use" and self._role == "assistant":
            self._flush_parts()
            self._items.append(self._tool_use(block))
            self._pending_tool_calls = True
            return
        if block_type in ("thinking", "redacted_thinking") and self._role == "assistant":
            self._thinking(block)
            return
        if block_type in ("server_tool_use", "web_search_tool_result") and self._role == "assistant":
            # The answer text that used the search is already part of the history.
            return
        if self._role == "user":
            # Tool results lead a user turn; any other content follows the call outputs.
            self._resolve_tool_calls()
        if block_type == "text":
            text = block.get("text")
            if not isinstance(text, str):
                raise MessagesRequestError("Text blocks require text")
            self._text(text)
        elif block_type in ("image", "document") and self._role == "user":
            self._parts.append(_media_part(block))
        else:
            raise MessagesRequestError(f"Content block type '{block_type}' is not supported in {self._role} messages")

    def _text(self, text: str) -> None:
        part_type = "output_text" if self._role == "assistant" else "input_text"
        self._parts.append({"type": part_type, "text": text})

    def _thinking(self, block: dict[str, JsonValue]) -> None:
        signature = block.get("signature")
        if block.get("type") != "thinking" or not is_proxy_signature(signature):
            return
        assert isinstance(signature, str)
        envelope = open_reasoning(signature, self._envelope_key)
        if envelope.model != self._model:
            return
        self._flush_parts()
        self._items.append(
            {
                "type": "reasoning",
                "id": envelope.item_id,
                "summary": [],
                "encrypted_content": envelope.encrypted_content,
            }
        )

    def _tool_use(self, block: dict[str, JsonValue]) -> dict[str, JsonValue]:
        call_id = block.get("id")
        name = block.get("name")
        if not isinstance(call_id, str) or not call_id or not isinstance(name, str) or not name:
            raise MessagesRequestError("tool_use blocks require an id and a name")
        return {
            "type": "function_call",
            "call_id": tool_alias(call_id),
            "name": tool_alias(name),
            "arguments": json.dumps(block.get("input") or {}, ensure_ascii=False, separators=(",", ":")),
        }

    def _tool_result(self, block: dict[str, JsonValue]) -> dict[str, JsonValue]:
        call_id = block.get("tool_use_id")
        if not isinstance(call_id, str) or not call_id:
            raise MessagesRequestError("tool_result blocks require a tool_use_id")
        content = block.get("content")
        output: JsonValue
        if content is None:
            output = ""
        elif isinstance(content, str):
            output = content
        elif isinstance(content, list):
            output = [_tool_result_part(part) for part in content]
        else:
            raise MessagesRequestError("tool_result content must be text or an array of content blocks")
        return {"type": "function_call_output", "call_id": tool_alias(call_id), "output": output}

    def _flush_parts(self) -> None:
        if self._parts:
            self._items.append({"type": "message", "role": self._role, "content": self._parts})
            self._parts = []

    def _resolve_tool_calls(self) -> None:
        self._pending_tool_calls = False
        self._flush_deferred()

    def _flush_deferred(self) -> None:
        if self._deferred_developer and not self._pending_tool_calls:
            self._items.extend(self._deferred_developer)
            self._deferred_developer = []


def _tool_result_part(part: JsonValue) -> JsonValue:
    if not isinstance(part, dict):
        raise MessagesRequestError("tool_result content blocks must be objects")
    if part.get("type") == "text":
        text = part.get("text")
        if not isinstance(text, str):
            raise MessagesRequestError("Text blocks require text")
        return {"type": "input_text", "text": text}
    if part.get("type") in ("image", "document"):
        return _media_part(part)
    raise MessagesRequestError(f"Content block type '{part.get('type')}' is not supported in tool results")


def _media_part(block: dict[str, JsonValue]) -> dict[str, JsonValue]:
    block_type = block.get("type")
    source = block.get("source")
    if not isinstance(source, dict):
        raise MessagesRequestError(f"{block_type} blocks require a source")
    source_type = source.get("type")
    media_type = source.get("media_type")
    data = source.get("data")
    url = source.get("url")
    if block_type == "image":
        if source_type == "base64" and isinstance(media_type, str) and isinstance(data, str):
            return {"type": "input_image", "image_url": f"data:{media_type};base64,{data}"}
        if source_type == "url" and isinstance(url, str):
            return {"type": "input_image", "image_url": url}
    else:
        if source_type == "base64" and media_type == "application/pdf" and isinstance(data, str):
            title = block.get("title")
            return {
                "type": "input_file",
                "filename": title if isinstance(title, str) and title else "document.pdf",
                "file_data": f"data:application/pdf;base64,{data}",
            }
        if source_type == "url" and isinstance(url, str):
            return {"type": "input_file", "file_url": url}
        if source_type == "text" and isinstance(data, str):
            return {"type": "input_text", "text": data}
    raise MessagesRequestError(f"Unsupported {block_type} source type '{source_type}'")
