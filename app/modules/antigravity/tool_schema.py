"""JSON Schema -> Gemini OpenAPI-subset compiler for Antigravity function declarations.

Cloud Code accepts function parameters only in Gemini's OpenAPI dialect (uppercase
types, no $ref, no oneOf/allOf), as the native CLI sends them. Only schema nodes
are transformed; literal data (property names, enum values, defaults) is never
rewritten (CLIProxyAPI's past whole-request sanitizer corrupted tool outputs).

Constraints Gemini cannot express are reported to the model in the description,
and the client still validates every call. A root union is relocated into the
validated "arguments" envelope shared with the Claude adapter.
"""

from __future__ import annotations

import json
from typing import cast
from urllib.parse import unquote

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError
from jsonschema.validators import validator_for
from pydantic import JsonValue

from app.core.openai.exceptions import ClientPayloadError
from app.modules.claude.tool_schema import MAX_SCHEMA_DEPTH, MAX_SCHEMA_NODES, ToolArguments

_TYPES = {
    "object": "OBJECT",
    "array": "ARRAY",
    "string": "STRING",
    "number": "NUMBER",
    "integer": "INTEGER",
    "boolean": "BOOLEAN",
}
_FORMATS = {"STRING": {"date-time", "enum"}, "NUMBER": {"float", "double"}, "INTEGER": {"int32", "int64"}}
_BOUNDS = ("minLength", "maxLength", "minItems", "maxItems", "minimum", "maximum", "minProperties", "maxProperties")
_ARGUMENT_KEY = "arguments"


def _literal(value: JsonValue) -> str:
    return json.dumps(value, ensure_ascii=False)


def _type_name(schema: JsonValue) -> str:
    return str(schema["type"]) if isinstance(schema, dict) and isinstance(schema.get("type"), str) else "any"


def compile_tool_schema(
    schema: dict[str, JsonValue], *, tool_name: str, param: str
) -> tuple[dict[str, JsonValue] | None, ToolArguments | None]:
    """Gemini parameters for a function (None when it takes no arguments) and its envelope codec."""

    def invalid(reason: str) -> ClientPayloadError:
        return ClientPayloadError(
            f"Antigravity tool '{tool_name}': {reason}", param=param, code="unsupported_parameter"
        )

    validator_type = validator_for(schema, default=Draft202012Validator)
    try:
        validator_type.check_schema(schema)
    except (SchemaError, RecursionError) as exc:
        raise invalid("invalid JSON Schema") from exc
    remaining = MAX_SCHEMA_NODES

    def resolve(reference: JsonValue, resolving: tuple[str, ...]) -> tuple[dict[str, JsonValue], tuple[str, ...]]:
        if not isinstance(reference, str) or not reference.startswith("#"):
            raise invalid("only local JSON-pointer schema references can be compiled")
        pointer = unquote(reference[1:])
        if pointer in resolving:
            raise invalid("recursive schema references cannot be expressed for Gemini")
        target: JsonValue = schema
        for token in pointer.split("/")[1:] if pointer else ():
            token = token.replace("~1", "/").replace("~0", "~")
            if not isinstance(target, dict) or token not in target:
                raise invalid("local reference must resolve to a schema")
            target = target[token]
        if not isinstance(target, dict):
            raise invalid("local reference must resolve to a schema object")
        return target, (*resolving, pointer)

    def flatten(node: dict[str, JsonValue], resolving: tuple[str, ...]) -> tuple[dict[str, JsonValue], tuple[str, ...]]:
        """Inline $ref and merge allOf, which Gemini cannot express, into one schema node."""
        while "$ref" in node:
            target, resolving = resolve(node["$ref"], resolving)
            node = {**target, **{key: value for key, value in node.items() if key != "$ref"}}
        members = node.get("allOf")
        if not isinstance(members, list):
            return node, resolving
        merged: dict[str, JsonValue] = {key: value for key, value in node.items() if key != "allOf"}
        for member in members:
            if not isinstance(member, dict):
                raise invalid("allOf members must be schema objects")
            part, resolving = flatten(member, resolving)
            for key, value in part.items():
                if key == "properties" and isinstance(value, dict):
                    properties = merged.setdefault("properties", {})
                    assert isinstance(properties, dict)
                    for name, child in value.items():
                        if name in properties and properties[name] != child:
                            raise invalid(f"allOf members declare conflicting property '{name}'")
                        properties[name] = child
                elif key == "required" and isinstance(value, list):
                    required = merged.setdefault("required", [])
                    assert isinstance(required, list)
                    required.extend(name for name in value if name not in required)
                elif key in merged and merged[key] != value and key not in ("description", "title"):
                    raise invalid(f"allOf members conflict on '{key}'")
                else:
                    merged.setdefault(key, value)
        return merged, resolving

    def compile_node(value: JsonValue, resolving: tuple[str, ...], depth: int) -> dict[str, JsonValue]:
        nonlocal remaining
        remaining -= 1
        if depth > MAX_SCHEMA_DEPTH or remaining < 0:
            raise invalid("schema exceeds the compilation complexity limit")
        if value is True:
            return {}
        if not isinstance(value, dict):
            raise invalid("schema nodes must be objects")
        node, resolving = flatten(value, resolving)
        notes: list[str] = []
        result: dict[str, JsonValue] = {}
        nullable = False
        branches: list[JsonValue] | None = None
        for key in ("anyOf", "oneOf"):
            options = node.get(key)
            if isinstance(options, list):
                if branches is not None:
                    raise invalid("anyOf and oneOf cannot be combined on one schema")
                branches = list(options)
                if key == "oneOf":
                    notes.append("exactly one alternative must match")
        declared = node.get("type")
        types = declared if isinstance(declared, list) else [declared] if isinstance(declared, str) else []
        if "null" in types:
            nullable = True
            types = [kind for kind in types if kind != "null"]
        if branches is not None:
            kept: list[JsonValue] = []
            for branch in branches:
                resolved = flatten(branch, resolving)[0] if isinstance(branch, dict) else branch
                if isinstance(resolved, dict) and resolved.get("type") == "null" and len(resolved) == 1:
                    nullable = True
                else:
                    kept.append(branch)
            if not kept:
                raise invalid("a schema that only allows null cannot be expressed for Gemini")
            if len(kept) == 1 and isinstance(kept[0], dict):
                base = {key: item for key, item in node.items() if key not in ("anyOf", "oneOf")}
                result = compile_node({**kept[0], **base}, resolving, depth + 1)
            else:
                result["anyOf"] = [compile_node(branch, resolving, depth + 1) for branch in kept]
        elif len(types) > 1:
            single = {key: item for key, item in node.items() if key != "type"}
            result["anyOf"] = [compile_node({**single, "type": kind}, resolving, depth + 1) for kind in types]
        else:
            kind = cast(str | None, types[0] if types else None)
            if kind is None and not nullable:
                kind = (
                    "object"
                    if "properties" in node
                    else "array"
                    if "items" in node or "prefixItems" in node
                    else "string"
                    if "enum" in node or "const" in node
                    else None
                )
            elif kind is None:
                raise invalid("a schema that only allows null cannot be expressed for Gemini")
            if kind is not None:
                if kind not in _TYPES:
                    raise invalid(f"unsupported schema type '{kind}'")
                result["type"] = _TYPES[kind]
            if kind == "object":
                properties = node.get("properties", {})
                if not isinstance(properties, dict):
                    raise invalid("properties must be an object")
                if properties:
                    result["properties"] = {
                        name: compile_node(child, resolving, depth + 1) for name, child in properties.items()
                    }
                required = node.get("required")
                if isinstance(required, list):
                    present = [name for name in required if name in properties]
                    if present:
                        result["required"] = present
                if isinstance(node.get("additionalProperties"), dict) and not properties:
                    notes.append("an object with free-form keys")
            elif kind == "array":
                items = node.get("items")
                prefix = node.get("prefixItems")
                if isinstance(prefix, list) and prefix:
                    notes.append("positional items: " + ", ".join(_type_name(item) for item in prefix))
                    result["items"] = {"anyOf": [compile_node(item, resolving, depth + 1) for item in prefix]}
                elif isinstance(items, dict) and items:
                    result["items"] = compile_node(items, resolving, depth + 1)
                else:
                    # Cloud Code rejects ARRAY without items; untyped elements are declared as text.
                    result["items"] = {"type": "STRING"}
                    notes.append("items may be any JSON value")
            enum = [node["const"]] if "const" in node else node.get("enum")
            if isinstance(enum, list):
                if kind == "string" and all(isinstance(item, str) for item in enum):
                    result["enum"] = enum
                else:
                    notes.append("allowed values: " + ", ".join(_literal(item) for item in enum))
            fmt = node.get("format")
            if isinstance(fmt, str) and kind is not None:
                if fmt in _FORMATS.get(_TYPES[kind], set()):
                    result["format"] = fmt
                else:
                    notes.append(f"format {fmt}")
            for bound in _BOUNDS:
                limit = node.get(bound)
                if isinstance(limit, (int, float)) and not isinstance(limit, bool):
                    result[bound] = limit
            if isinstance(node.get("pattern"), str):
                notes.append(f"pattern {node['pattern']}")
        if isinstance(node.get("title"), str):
            result["title"] = node["title"]
        description = node.get("description")
        if notes or isinstance(description, str):
            text = description if isinstance(description, str) else ""
            if notes:
                text = (text + " " if text else "") + "(" + "; ".join(notes) + ")"
            result["description"] = text
        if nullable:
            result["nullable"] = True
        return result

    root, _ = flatten(schema, ())
    if root.get("type") not in (None, "object"):
        raise invalid("function parameters must describe an object")
    if "anyOf" in root or "oneOf" in root:
        relocated = compile_node(schema, (), 1)
        return (
            {"type": "OBJECT", "properties": {_ARGUMENT_KEY: relocated}, "required": [_ARGUMENT_KEY]},
            ToolArguments(tool_name, validator_type(schema), provider="Antigravity"),
        )
    compiled = compile_node({**root, "type": "object"}, (), 0)
    return (compiled, None) if "properties" in compiled else (None, None)
