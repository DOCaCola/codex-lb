"""Responses Lite tool bundles for upstreams that declare tools only in ``tools``.

With Responses Lite, Codex records every change of its tool catalog as an ``additional_tools`` input item and
keeps those items in history after a switch to a model without Responses Lite. Such an upstream receives the
bundled declarations merged into ``tools``, as CLIProxyAPI (``responsesToolSources``) and OmniRoute
(``collectResponsesTools``) do: top-level declarations as sent, then each bundle in history order, the first
declaration of a tool winning and same-named namespaces merging their members.

Responses Lite groups plain functions under the reserved ``functions`` namespace, which Codex treats as no
namespace (``ToolRouter::build_tool_call``). Its members merge as top-level tools, and calls recorded under it
are calls without a namespace, as in opencodex and OmniRoute.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.core.openai.exceptions import ClientPayloadError
from app.core.types import JsonValue
from app.core.utils.json_guards import is_json_dict, is_json_list

ADDITIONAL_TOOLS = "additional_tools"
DEFAULT_FUNCTION_NAMESPACE = "functions"
_CALL_TYPES = frozenset({"function_call", "custom_tool_call"})

type _ToolKey = tuple[str, str | None, str]


def client_tool_namespace(namespace: str | None) -> str | None:
    """The namespace of a client tool; the reserved ``functions`` namespace is none."""
    return None if namespace in (None, "", DEFAULT_FUNCTION_NAMESPACE) else namespace


def additional_tool_bundles(items: Sequence[JsonValue]) -> list[list[JsonValue]]:
    """The declarations of every ``additional_tools`` item, in history order."""
    bundles: list[list[JsonValue]] = []
    for index, item in enumerate(items):
        if is_json_dict(item) and item.get("type") == ADDITIONAL_TOOLS:
            tools = item.get("tools")
            if not is_json_list(tools):
                raise ClientPayloadError("additional_tools requires a tools array", param=f"input[{index}].tools")
            bundles.append(tools)
    return bundles


def collect_responses_tools(tools: Sequence[JsonValue], bundles: list[list[JsonValue]]) -> list[JsonValue]:
    """Top-level declarations unchanged, followed by the bundled declarations they do not already make.

    Malformed declarations are kept for the projection to reject.
    """
    merged = list(tools)
    if not bundles:
        return merged
    seen: set[_ToolKey | None] = set()
    namespaces: dict[str, int] = {}
    for position, tool in enumerate(merged):
        namespace = _namespace(tool)
        if namespace is None:
            seen.add(_key(tool, None))
            continue
        name, members = namespace
        namespaces.setdefault(name, position)
        seen.update(_key(member, name) for member in members)

    def claimed(tool: JsonValue, namespace: str | None) -> bool:
        key = _key(tool, namespace)
        if key is not None and key in seen:
            return False
        seen.add(key)
        return True

    for bundle in bundles:
        for tool in bundle:
            namespace = _namespace(tool)
            if namespace is None:
                if claimed(tool, None):
                    merged.append(tool)
                continue
            name, members = namespace
            if client_tool_namespace(name) is None:
                merged.extend(member for member in members if claimed(member, None))
                continue
            added = [member for member in members if claimed(member, name)]
            position = namespaces.get(name)
            if position is None:
                if added:
                    namespaces[name] = len(merged)
                    merged.append({**_dict(tool), "tools": added})
            elif added:
                existing = _dict(merged[position])
                merged[position] = {**existing, "tools": [*_list(existing["tools"]), *added]}
    return merged


def merge_additional_tools(payload: dict[str, JsonValue]) -> dict[str, JsonValue]:
    """A Responses request with its bundles merged into ``tools`` and calls named without the reserved namespace."""
    items = payload.get("input")
    if not is_json_list(items):
        return payload
    bundles = additional_tool_bundles(items)
    if not bundles and not any(_reserved_namespace_call(item) for item in items):
        return payload
    result = dict(payload)
    if bundles:
        tools = payload.get("tools", [])
        if not is_json_list(tools):
            raise ClientPayloadError("Tools must be an array", param="tools")
        result["tools"] = collect_responses_tools(tools, bundles)
    result["input"] = [
        {key: value for key, value in item.items() if key != "namespace"}
        if is_json_dict(item) and _reserved_namespace_call(item)
        else item
        for item in items
        if not (is_json_dict(item) and item.get("type") == ADDITIONAL_TOOLS)
    ]
    return result


def _reserved_namespace_call(item: JsonValue) -> bool:
    return (
        is_json_dict(item)
        and item.get("type") in _CALL_TYPES
        and "namespace" in item
        and item["namespace"] in ("", DEFAULT_FUNCTION_NAMESPACE)
    )


def _namespace(tool: JsonValue) -> tuple[str, list[JsonValue]] | None:
    if not is_json_dict(tool) or tool.get("type") != "namespace":
        return None
    name, members = tool.get("name"), tool.get("tools")
    if not isinstance(name, str) or not is_json_list(members):
        return None
    return name, members


def _key(tool: JsonValue, namespace: str | None) -> _ToolKey | None:
    """A named tool is identified by namespace and name; a nameless hosted tool by its type."""
    if not is_json_dict(tool):
        return None
    name, kind = tool.get("name"), tool.get("type")
    if isinstance(name, str) and name:
        return ("tool", client_tool_namespace(namespace), name)
    if isinstance(kind, str) and namespace is None:
        return ("hosted", None, kind)
    return None


def _dict(value: JsonValue) -> dict[str, JsonValue]:
    assert is_json_dict(value)
    return value


def _list(value: JsonValue) -> list[JsonValue]:
    assert is_json_list(value)
    return value
