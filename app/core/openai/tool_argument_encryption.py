"""Plaintext declarations for tool calls produced outside the OpenAI backend.

Codex marks some function parameters ``encrypted``. The OpenAI backend encrypts
those arguments and lists the encrypted ones on each ``function_call`` in
``encrypted_function_args``. Other providers return the same arguments as
plaintext, so their calls must state an empty list; otherwise Codex treats the
plaintext as ciphertext (for example when delivering a subagent task).
"""

from __future__ import annotations

from app.core.types import JsonValue

ToolKey = tuple[str | None, str]


def declares_encrypted_arguments(parameters: JsonValue) -> bool:
    if not isinstance(parameters, dict):
        return False
    properties = parameters.get("properties")
    return isinstance(properties, dict) and any(
        isinstance(schema, dict) and schema.get("encrypted") is True for schema in properties.values()
    )


def tools_with_encrypted_arguments(tools: JsonValue) -> frozenset[ToolKey]:
    if not isinstance(tools, list):
        return frozenset()
    keys: set[ToolKey] = set()

    def collect(tool: JsonValue, namespace: str | None) -> None:
        if not isinstance(tool, dict):
            return
        name = tool.get("name")
        if not isinstance(name, str):
            return
        if tool.get("type") == "namespace":
            children = tool.get("tools")
            if isinstance(children, list):
                for child in children:
                    collect(child, name)
        elif tool.get("type") == "function" and declares_encrypted_arguments(tool.get("parameters")):
            keys.add((namespace, name))

    for tool in tools:
        collect(tool, None)
    return frozenset(keys)


def mark_plaintext_arguments(item: JsonValue, tools: frozenset[ToolKey]) -> None:
    if not isinstance(item, dict) or item.get("type") != "function_call":
        return
    namespace, name = item.get("namespace"), item.get("name")
    if (namespace if isinstance(namespace, str) else None, name) in tools:
        item["encrypted_function_args"] = []
