import pytest

from app.core.openai.additional_tools import collect_responses_tools, merge_additional_tools
from app.core.openai.exceptions import ClientPayloadError
from app.core.types import JsonValue

pytestmark = pytest.mark.unit


def _function(name, description=""):
    return {"type": "function", "name": name, "description": description, "parameters": {"type": "object"}}


def _namespace(name, *tools):
    return {"type": "namespace", "name": name, "description": name, "tools": list(tools)}


def _bundle(*tools):
    return {"type": "additional_tools", "role": "developer", "tools": list(tools)}


def test_top_level_tools_are_returned_unchanged_without_bundles():
    tools = [_function("a"), _function("a")]
    assert collect_responses_tools(tools, []) == tools


def test_bundles_add_only_tools_not_declared_earlier():
    """Top level first, then bundles in history order; the first declaration wins (OmniRoute collectResponsesTools)."""
    merged = collect_responses_tools(
        [_function("exec_command", "top"), _namespace("mcp__docs", _function("search", "top"))],
        [
            [
                _namespace("functions", _function("exec_command", "lite"), _function("view_image", "first")),
                _namespace("mcp__docs", _function("search", "lite"), _function("fetch")),
                {"type": "web_search", "external_web_access": True},
                _namespace("mcp__new", _function("run")),
            ],
            [
                _function("view_image", "later"),
                {"type": "web_search", "external_web_access": False},
                _namespace("mcp__new", _function("run", "later")),
            ],
        ],
    )
    assert merged == [
        _function("exec_command", "top"),
        _namespace("mcp__docs", _function("search", "top"), _function("fetch")),
        _function("view_image", "first"),
        {"type": "web_search", "external_web_access": True},
        _namespace("mcp__new", _function("run")),
    ]


def test_merge_projects_bundles_onto_tools_and_drops_the_reserved_call_namespace():
    call = {"type": "function_call", "call_id": "c", "name": "view_image", "namespace": "functions", "arguments": "{}"}
    mcp_call = {**call, "call_id": "m", "name": "run", "namespace": "mcp__new"}
    payload: dict[str, JsonValue] = {
        "model": "m",
        "tools": [_function("exec_command")],
        "input": [_bundle(_namespace("functions", _function("view_image"))), call, mcp_call],
    }
    merged = merge_additional_tools(payload)
    assert merged["tools"] == [_function("exec_command"), _function("view_image")]
    assert merged["input"] == [{key: value for key, value in call.items() if key != "namespace"}, mcp_call]
    assert call["namespace"] == "functions"


def test_merge_leaves_requests_without_lite_history_untouched():
    payload: dict[str, JsonValue] = {
        "model": "m",
        "input": [{"type": "function_call", "call_id": "c", "name": "a", "arguments": "{}"}],
    }
    assert merge_additional_tools(payload) is payload


def test_merge_rejects_a_bundle_without_tools():
    with pytest.raises(ClientPayloadError) as rejected:
        merge_additional_tools({"model": "m", "input": [{"type": "additional_tools", "role": "developer"}]})
    assert rejected.value.param == "input[0].tools"
