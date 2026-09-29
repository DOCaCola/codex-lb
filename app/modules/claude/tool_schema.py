"""Lossless schema relocation and argument encoding for translated Claude tools."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from urllib.parse import quote, unquote

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError
from jsonschema.protocols import Validator
from jsonschema.validators import validator_for
from pydantic import JsonValue

from app.core.openai.exceptions import ClientPayloadError
from app.modules.claude.credentials import ClaudeError

MAX_SCHEMA_DEPTH = 64
MAX_SCHEMA_NODES = 4096
MAX_TOOL_ARGUMENT_BYTES = 2 * 1024 * 1024
_ARGUMENT_KEY = "arguments"
_COMPOSITIONS = {"oneOf", "anyOf", "allOf"}
_MAPS = {"properties", "patternProperties", "$defs", "definitions", "dependentSchemas"}
_SINGLE = {
    "additionalProperties",
    "unevaluatedProperties",
    "additionalItems",
    "unevaluatedItems",
    "contains",
    "propertyNames",
    "not",
    "if",
    "then",
    "else",
    "contentSchema",
}
_SCOPES = {"$id", "id", "$anchor", "$dynamicAnchor", "$dynamicRef", "$recursiveAnchor", "$recursiveRef"}
_DIALECTS = {
    "http://json-schema.org/draft-07/schema#",
    "https://json-schema.org/draft-07/schema",
    "https://json-schema.org/draft/2019-09/schema",
    "https://json-schema.org/draft/2020-12/schema",
}


@dataclass(frozen=True)
class ToolArguments:
    """Only adapted tools need a codec; ordinary tool arguments remain untouched."""

    tool_name: str
    validator: Validator

    def encode(self, arguments: dict[str, JsonValue]) -> dict[str, JsonValue]:
        return {_ARGUMENT_KEY: arguments}

    def parse(self, raw: str) -> JsonValue:
        def reject_constant(value: str) -> JsonValue:
            raise ValueError("Non-JSON number")

        def object_pairs(pairs: list[tuple[str, JsonValue]]) -> dict[str, JsonValue]:
            result: dict[str, JsonValue] = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError("Duplicate JSON member")
                result[key] = value
            return result

        try:
            return json.loads(raw, parse_constant=reject_constant, object_pairs_hook=object_pairs)
        except (ValueError, RecursionError) as exc:
            raise ClaudeError(f"Claude tool '{self.tool_name}' returned invalid argument JSON") from exc

    def decode(self, envelope: dict[str, JsonValue]) -> dict[str, JsonValue]:
        try:
            size = len(json.dumps(envelope, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode())
        except (ValueError, RecursionError) as exc:
            raise ClaudeError(f"Claude tool '{self.tool_name}' returned invalid argument JSON") from exc
        if size > MAX_TOOL_ARGUMENT_BYTES:
            raise ClaudeError(f"Claude tool '{self.tool_name}' arguments exceeded the size limit")
        arguments = envelope.get(_ARGUMENT_KEY)
        if set(envelope) != {_ARGUMENT_KEY} or not isinstance(arguments, dict):
            raise ClaudeError(f"Claude tool '{self.tool_name}' returned an invalid arguments envelope")
        try:
            self.validator.validate(arguments)
        except (ValidationError, RecursionError) as exc:
            # Never include provider argument values in diagnostics.
            raise ClaudeError(f"Claude tool '{self.tool_name}' arguments do not match its declared schema") from exc
        return arguments


def adapt_tool_schema(
    schema: dict[str, JsonValue], *, tool_name: str, param: str
) -> tuple[dict[str, JsonValue], ToolArguments | None]:
    def invalid(reason: str) -> ClientPayloadError:
        return ClientPayloadError(
            f"Claude tool '{tool_name}': {reason}",
            param=param,
            code="unsupported_parameter",
        )

    root_type = schema.get("type")
    if "type" in schema and root_type != "object":
        raise invalid("function parameters must describe an object")
    if not (_COMPOSITIONS & schema.keys() or "$ref" in schema):
        # Adding object type/properties does not change the function argument domain.
        return {"type": "object", "properties": {}, **schema}, None

    schema_paths: set[tuple[str, ...]] = set()
    references: list[tuple[str, ...]] = []
    remaining = MAX_SCHEMA_NODES

    def walk(value: JsonValue, path: tuple[str, ...], *, schema_node: bool, depth: int) -> JsonValue:
        nonlocal remaining
        remaining -= 1
        if depth > MAX_SCHEMA_DEPTH or remaining < 0:
            raise invalid("schema exceeds the adaptation complexity limit")
        if schema_node:
            schema_paths.add(path)
        if isinstance(value, list):
            return [walk(item, (*path, str(i)), schema_node=False, depth=depth + 1) for i, item in enumerate(value)]
        if not isinstance(value, dict):
            return value
        if schema_node and (_SCOPES & value.keys()):
            raise invalid("schema identifiers, anchors and dynamic reference scopes cannot be relocated")
        result: dict[str, JsonValue] = {}
        for key, child in value.items():
            child_path = (*path, key)
            if schema_node and key == "$schema":
                if path or not isinstance(child, str) or child not in _DIALECTS:
                    raise invalid("unsupported schema dialect or nested dialect change")
            if schema_node and key == "$ref":
                if not isinstance(child, str) or not child.startswith("#"):
                    raise invalid("only local JSON-pointer schema references can be relocated")
                try:
                    if re.search(r"%(?![0-9a-fA-F]{2})", child):
                        raise ValueError("invalid percent escape")
                    pointer = unquote(child[1:], errors="strict")
                except (ValueError, UnicodeError) as exc:
                    raise invalid("invalid JSON-pointer URI encoding") from exc
                if pointer and not pointer.startswith("/"):
                    raise invalid("named schema anchors cannot be relocated")
                if re.search(r"~(?![01])", pointer):
                    raise invalid("invalid JSON-pointer schema reference")
                tokens = (
                    tuple(part.replace("~1", "/").replace("~0", "~") for part in pointer[1:].split("/"))
                    if pointer
                    else ()
                )
                references.append(tokens)
                result[key] = "#/properties/arguments" + quote(pointer, safe="/~$")
            elif schema_node and key in _MAPS and isinstance(child, dict):
                result[key] = {
                    name: walk(item, (*child_path, name), schema_node=True, depth=depth + 2)
                    for name, item in child.items()
                }
            elif schema_node and key == "dependencies" and isinstance(child, dict):
                result[key] = {
                    name: walk(item, (*child_path, name), schema_node=isinstance(item, (dict, bool)), depth=depth + 2)
                    for name, item in child.items()
                }
            elif schema_node and (key in _COMPOSITIONS or key in {"prefixItems", "items"}) and isinstance(child, list):
                result[key] = [
                    walk(item, (*child_path, str(i)), schema_node=True, depth=depth + 2) for i, item in enumerate(child)
                ]
            else:
                result[key] = walk(
                    child, child_path, schema_node=schema_node and key in (_SINGLE | {"items"}), depth=depth + 1
                )
        return result

    relocated = walk(schema, (), schema_node=True, depth=0)
    assert isinstance(relocated, dict)
    if any(target not in schema_paths for target in references):
        raise invalid("local reference must resolve to a schema, not missing or literal data")
    validator_type = validator_for(schema, default=Draft202012Validator)
    try:
        validator_type.check_schema(schema)
    except (SchemaError, RecursionError) as exc:
        raise invalid("invalid JSON Schema") from exc
    result: dict[str, JsonValue] = {
        "type": "object",
        "properties": {_ARGUMENT_KEY: relocated},
        "required": [_ARGUMENT_KEY],
        "additionalProperties": False,
    }
    # A dialect declaration governs the entire relocated document.
    if "$schema" in relocated:
        result["$schema"] = relocated.pop("$schema")
    return result, ToolArguments(tool_name, validator_type(schema))
