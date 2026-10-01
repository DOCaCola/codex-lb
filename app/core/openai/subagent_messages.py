"""Inter-agent messages that every provider in one agent tree can read.

OpenAI reserves the Codex ``collaboration`` tool namespace: its schema must
match exactly, and it marks ``message`` parameters ``encrypted``. The backend
then returns those messages as ciphertext that only OpenAI can read. codex-lb
routes one agent tree across OpenAI, Claude and model sources, so the native
boundary declares the namespace as ``UPSTREAM_NAMESPACE`` without encryption
and restores native output to ``collaboration`` with
``encrypted_function_args: []``, Codex's plaintext delivery contract.
Translated providers receive the resulting ``agent_message`` items as user
messages. Their sender and recipient travel in Codex's own message header,
because user messages have no fields for them.
"""

from __future__ import annotations

from collections.abc import Mapping

from app.core.openai.exceptions import ClientPayloadError
from app.core.types import JsonValue
from app.core.utils.json_guards import is_json_list, is_json_mapping

NAMESPACE = "collaboration"
UPSTREAM_NAMESPACE = "collaboration-optimize"


def _plaintext_tool(tool: JsonValue) -> JsonValue:
    if not is_json_mapping(tool):
        return tool
    parameters = tool.get("parameters")
    properties = parameters.get("properties") if is_json_mapping(parameters) else None
    if not is_json_mapping(parameters) or not is_json_mapping(properties):
        return tool
    plaintext = {
        name: {key: value for key, value in schema.items() if key != "encrypted"} if is_json_mapping(schema) else schema
        for name, schema in properties.items()
    }
    return {**tool, "parameters": {**parameters, "properties": plaintext}}


def _project_tools(tools: list[JsonValue]) -> list[JsonValue] | None:
    projected: list[JsonValue] | None = None
    for index, tool in enumerate(tools):
        if is_json_mapping(tool) and tool.get("type") == "namespace" and tool.get("name") == NAMESPACE:
            children = tool.get("tools")
            projected = projected or list(tools)
            projected[index] = {
                **tool,
                "name": UPSTREAM_NAMESPACE,
                "tools": [_plaintext_tool(child) for child in children] if is_json_list(children) else children,
            }
    return projected


def project_native_collaboration_tools(payload: Mapping[str, JsonValue]) -> dict[str, JsonValue]:
    """Declare collaboration tools under the unreserved upstream namespace.

    Returns a new top-level mapping; the caller's tools and input are not
    mutated. History items keep their client namespace.
    """
    projected = dict(payload)
    tools = payload.get("tools")
    if is_json_list(tools) and (projected_tools := _project_tools(tools)) is not None:
        projected["tools"] = projected_tools
    items = payload.get("input")
    if is_json_list(items):
        projected_items: list[JsonValue] | None = None
        for index, item in enumerate(items):
            if not is_json_mapping(item) or item.get("type") != "additional_tools":
                continue
            bundle = item.get("tools")
            if is_json_list(bundle) and (projected_bundle := _project_tools(bundle)) is not None:
                projected_items = projected_items or list(items)
                projected_items[index] = {**item, "tools": projected_bundle}
        if projected_items is not None:
            projected["input"] = projected_items
    return projected


def restore_native_collaboration(value: JsonValue) -> JsonValue | None:
    """Return a copy with upstream collaboration names restored, or ``None``.

    Function calls also state ``encrypted_function_args: []`` because their
    arguments are plaintext. ``value`` is never mutated.
    """
    if is_json_list(value):
        restored_list: list[JsonValue] | None = None
        for index, child in enumerate(value):
            if (restored_child := restore_native_collaboration(child)) is not None:
                restored_list = restored_list or list(value)
                restored_list[index] = restored_child
        return restored_list
    if not is_json_mapping(value):
        return None
    restored: dict[str, JsonValue] | None = None
    kind = value.get("type")
    if kind == "function_call" and value.get("namespace") == UPSTREAM_NAMESPACE:
        restored = {**value, "namespace": NAMESPACE, "encrypted_function_args": []}
    elif kind == "namespace" and value.get("name") == UPSTREAM_NAMESPACE:
        restored = {**value, "name": NAMESPACE}
    for key, child in value.items():
        if isinstance(child, (dict, list)) and (restored_child := restore_native_collaboration(child)) is not None:
            restored = restored or dict(value)
            restored[key] = restored_child
    return restored


def agent_message_as_user_message(item: Mapping[str, JsonValue], *, index: int) -> dict[str, JsonValue]:
    """Lower a Codex ``agent_message`` to a standard user message."""
    content = item.get("content")
    if not is_json_list(content):
        raise ClientPayloadError("Agent message content must be an array", param=f"input[{index}].content")
    author, recipient = item.get("author"), item.get("recipient")
    if not isinstance(author, str) or not isinstance(recipient, str):
        raise ClientPayloadError("Agent messages require an author and recipient", param=f"input[{index}]")
    if any(is_json_mapping(part) and part.get("type") == "encrypted_content" for part in content):
        raise ClientPayloadError(
            "This subagent message is encrypted for OpenAI models only; respawn the subagent to continue.",
            param=f"input[{index}]",
            code="nonportable_agent_message",
        )
    # Codex's header for agent messages (``InterAgentCommunication``).
    header: JsonValue = {"type": "input_text", "text": f"Task name: {recipient}\nSender: {author}\nPayload:\n"}
    return {"type": "message", "role": "user", "content": [header, *content]}


def lower_agent_messages(payload: Mapping[str, JsonValue]) -> dict[str, JsonValue]:
    """Return ``payload`` with every ``agent_message`` input lowered."""
    lowered = dict(payload)
    items = payload.get("input")
    if is_json_list(items) and any(is_json_mapping(item) and item.get("type") == "agent_message" for item in items):
        lowered["input"] = [
            agent_message_as_user_message(item, index=index)
            if is_json_mapping(item) and item.get("type") == "agent_message"
            else item
            for index, item in enumerate(items)
        ]
    return lowered
