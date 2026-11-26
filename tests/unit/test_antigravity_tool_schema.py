from __future__ import annotations

from typing import Any

import pytest

from app.core.openai.exceptions import ClientPayloadError
from app.modules.antigravity.tool_schema import (
    MAX_COPIED_REQUEST_BYTES,
    MAX_COPIED_SCHEMA_BYTES,
    ReferenceCopyBudget,
    compile_tool_schema,
)


def _compile(schema: dict[str, Any], budget: ReferenceCopyBudget | None = None):
    return compile_tool_schema(
        schema,  # type: ignore[arg-type]
        tool_name="tool",
        param="tools[0].parameters",
        budget=budget or ReferenceCopyBudget(),
    )


def _shared(definition: dict[str, Any], references: int) -> dict[str, Any]:
    """An object whose properties all reference one shared definition."""
    return {
        "type": "object",
        "$defs": {"shared": definition},
        "properties": {f"p{index:04d}": {"$ref": "#/$defs/shared"} for index in range(references)},
    }


# About 14 KB of literal enum data per copy.
_LARGE_ENUM = {"type": "string", "enum": [f"value_{index:04d}" for index in range(1_000)]}


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


def test_reference_fan_out_beyond_the_schema_limit_is_rejected() -> None:
    schema = _shared(_LARGE_ENUM, 400)
    assert len(str(schema).encode()) < 40_000

    with pytest.raises(ClientPayloadError, match="schema references expand beyond the size limit") as raised:
        _compile(schema)
    assert raised.value.param == "tools[0].parameters"
    assert raised.value.code == "unsupported_parameter"


def test_schemas_without_references_are_never_charged() -> None:
    budget = ReferenceCopyBudget()
    literal = {"type": "string", "enum": [f"value_{index:05d}" for index in range(30_000)]}
    parameters, _ = _compile({"type": "object", "properties": {"mode": literal}}, budget)

    assert parameters is not None
    assert len(str(parameters).encode()) > MAX_COPIED_SCHEMA_BYTES
    assert budget == ReferenceCopyBudget()


def test_copies_within_the_limit_are_charged_and_compiled() -> None:
    budget = ReferenceCopyBudget()
    parameters, _ = _compile(_shared(_LARGE_ENUM, 16), budget)

    assert parameters is not None
    assert len(parameters["properties"]) == 16  # type: ignore[arg-type, index]
    assert budget.nodes == 16
    assert 16 * 14_000 < budget.bytes <= MAX_COPIED_SCHEMA_BYTES


def test_request_byte_limit_spans_declarations() -> None:
    schema = _shared(_LARGE_ENUM, 16)
    single = ReferenceCopyBudget()
    _compile(schema, single)

    budget = ReferenceCopyBudget()
    compiled = 0
    with pytest.raises(ClientPayloadError, match="in this request expand beyond the size limit"):
        while True:
            _compile(schema, budget)
            compiled += 1
    assert compiled == MAX_COPIED_REQUEST_BYTES // single.bytes


def test_request_node_limit_spans_declarations() -> None:
    budget = ReferenceCopyBudget()
    schema = _shared({"type": "string"}, 3_000)
    for _ in range(16):
        _compile(schema, budget)
    assert budget.nodes == 48_000

    with pytest.raises(ClientPayloadError, match="in this request expand beyond the size limit"):
        _compile(schema, budget)
