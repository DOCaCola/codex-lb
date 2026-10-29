from __future__ import annotations

from typing import Any

import pytest

from app.core.openai.exceptions import ClientPayloadError
from app.modules.antigravity.tool_schema import compile_tool_schema


def _compile(schema: dict[str, Any]):
    return compile_tool_schema(schema, tool_name="tool", param="tools[0].parameters")  # type: ignore[arg-type]


def test_openapi_dialect_with_nullable_and_formats() -> None:
    parameters, arguments = _compile(
        {
            "type": "object",
            "properties": {
                "when": {"type": ["string", "null"], "format": "date-time"},
                "mode": {"enum": ["a", "b"], "type": "string"},
                "count": {"type": "integer", "minimum": 1},
                "tags": {"type": "array"},
            },
            "required": ["mode", "missing"],
        }
    )
    assert arguments is None
    assert parameters == {
        "type": "OBJECT",
        "properties": {
            "when": {"type": "STRING", "format": "date-time", "nullable": True},
            "mode": {"type": "STRING", "enum": ["a", "b"]},
            "count": {"type": "INTEGER", "minimum": 1},
            "tags": {"type": "ARRAY", "items": {"type": "STRING"}, "description": "(items may be any JSON value)"},
        },
        "required": ["mode"],
    }


def test_refs_and_all_of_are_inlined() -> None:
    parameters, _ = _compile(
        {
            "$defs": {"path": {"type": "string", "description": "A path"}},
            "allOf": [
                {"type": "object", "properties": {"path": {"$ref": "#/$defs/path"}}, "required": ["path"]},
                {"properties": {"recursive": {"type": "boolean"}}},
            ],
        }
    )
    assert parameters == {
        "type": "OBJECT",
        "properties": {"path": {"type": "STRING", "description": "A path"}, "recursive": {"type": "BOOLEAN"}},
        "required": ["path"],
    }


def test_root_alternatives_are_enveloped_and_decoded() -> None:
    parameters, arguments = _compile(
        {
            "oneOf": [
                {"type": "object", "properties": {"a": {"type": "string"}}, "required": ["a"]},
                {"type": "object", "properties": {"b": {"type": "integer"}}, "required": ["b"]},
            ]
        }
    )
    assert parameters is not None
    assert parameters["required"] == ["arguments"]
    assert arguments is not None
    assert arguments.decode(arguments.encode({"b": 2})) == {"b": 2}


def test_empty_object_takes_no_parameters() -> None:
    assert _compile({"type": "object", "properties": {}}) == (None, None)


@pytest.mark.parametrize(
    "schema",
    [
        {"type": "string"},
        {"type": "object", "properties": {"x": {"$ref": "https://example.com/s"}}},
        {"$defs": {"n": {"type": "object", "properties": {"n": {"$ref": "#/$defs/n"}}}}, "$ref": "#/$defs/n"},
        {"type": "object", "properties": {"x": {"type": "null"}}},
    ],
)
def test_inexpressible_schemas_are_rejected(schema: dict[str, Any]) -> None:
    with pytest.raises(ClientPayloadError) as raised:
        _compile(schema)
    assert raised.value.param == "tools[0].parameters"
