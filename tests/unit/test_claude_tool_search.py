"""Codex client tool search on Claude: Anthropic custom tool search over deferred tools."""

import logging

import pytest
from cryptography.fernet import Fernet
from pydantic import JsonValue

from app.core.crypto import TokenEncryptor
from app.core.openai.exceptions import ClientPayloadError
from app.modules.claude.cache_lineage import CacheLineage
from app.modules.claude.caching import cache_translated
from app.modules.claude.capabilities import reasoning_spec
from app.modules.claude.opaque import ClaudeOpaqueState, OpaqueScope
from app.modules.claude.protocol import defers_tools, project_responses
from app.modules.claude.responses import ResponsesProjection
from tests.claude_json_helpers import at

pytestmark = pytest.mark.unit

# Codex's client tool search declaration (codex-rs tools ToolSpec::ToolSearch).
SEARCH_TOOL: dict[str, JsonValue] = {
    "type": "tool_search",
    "execution": "client",
    "description": "Search deferred tools. Sources: codex_app (Desktop app actions).",
    "parameters": {
        "type": "object",
        "properties": {"query": {"type": "string"}, "limit": {"type": "number"}},
        "required": ["query"],
        "additionalProperties": False,
    },
}
SHELL = {"type": "function", "name": "shell", "parameters": {"type": "object", "properties": {}}}
CANVAS = {
    "type": "namespace",
    "name": "mcp__codex_app__",
    "description": "Desktop app actions",
    "tools": [
        {
            "type": "function",
            "name": "create_canvas",
            "description": "Create a canvas.",
            "defer_loading": True,
            "parameters": {"type": "object", "properties": {"title": {"type": "string"}}},
        }
    ],
}


def project(payload: dict[str, JsonValue]):
    model = str(payload.get("model", ""))
    return project_responses(payload, max_output_tokens=8192, reasoning=reasoning_spec(model, None))


def request(tools: list[JsonValue], items: list[JsonValue]) -> dict[str, JsonValue]:
    return {"model": "anthropic/claude-opus-5-5", "tools": tools, "input": items}


def search_call(call_id: str = "search1") -> dict[str, JsonValue]:
    return {
        "type": "tool_search_call",
        "call_id": call_id,
        "execution": "client",
        "status": "completed",
        "arguments": {"query": "canvas", "limit": 1},
    }


def search_output(tools: list[JsonValue], call_id: str = "search1") -> dict[str, JsonValue]:
    return {
        "type": "tool_search_output",
        "call_id": call_id,
        "status": "completed",
        "execution": "client",
        "tools": tools,
    }


USER = {"role": "user", "content": "Make a canvas"}


def test_search_tool_is_a_cached_declaration_and_loaded_tools_are_deferred_references():
    before = project(request([SHELL, SEARCH_TOOL], [USER]))
    after = project(request([SHELL, SEARCH_TOOL], [USER, search_call(), search_output([CANVAS])]))

    tools = after.body["tools"]
    assert isinstance(tools, list)
    # The cached prefix (non-deferred tools) is identical before and after the load.
    assert [tool for tool in tools if isinstance(tool, dict) and not tool.get("defer_loading")] == before.body["tools"]
    assert at(before.body, "tools", 1, "name") == "ToolSearch"
    assert at(before.body, "tools", 1, "input_schema", "required") == ["query"]
    loaded = at(after.body, "tools", 2)
    assert isinstance(loaded, dict)
    assert loaded["defer_loading"] is True
    assert after.tools.by_wire[str(loaded["name"])].namespace == "mcp__codex_app__"
    assert at(after.body, "messages", 1, "content") == [
        {"type": "tool_use", "id": "search1", "name": "ToolSearch", "input": {"query": "canvas", "limit": 1}}
    ]
    assert at(after.body, "messages", 2, "content") == [
        {
            "type": "tool_result",
            "tool_use_id": "search1",
            "content": [{"type": "tool_reference", "tool_name": loaded["name"]}],
        }
    ]
    assert defers_tools(after.body) and not defers_tools(before.body)


def test_repeated_loads_declare_each_tool_once_and_reference_it_every_time():
    items = [USER, search_call("s1"), search_output([CANVAS], "s1"), search_call("s2"), search_output([CANVAS], "s2")]
    projected = project(request([SEARCH_TOOL], items))
    tools = projected.body["tools"]
    assert isinstance(tools, list) and len(tools) == 2
    name = at(projected.body, "tools", 1, "name")
    for index in (2, 4):
        assert at(projected.body, "messages", index, "content", 0, "content") == [
            {"type": "tool_reference", "tool_name": name}
        ]


def test_loaded_tools_are_ordinary_declarations_without_a_search_tool():
    # A tool-less request (local compaction) cannot defer every tool; Anthropic rejects that.
    projected = project(request([], [USER, search_call(), search_output([CANVAS])]))
    tools = projected.body["tools"]
    assert isinstance(tools, list) and len(tools) == 1
    assert "defer_loading" not in at(projected.body, "tools", 0)
    assert at(projected.body, "messages", 1, "content", 0, "name") == "ToolSearch"


def test_empty_and_standalone_search_results_are_text():
    empty = project(request([SEARCH_TOOL], [USER, search_call(), search_output([])]))
    assert at(empty.body, "messages", 2, "content", 0, "content") == [
        {"type": "text", "text": "No matching tools found."}
    ]

    standalone = project(request([SEARCH_TOOL], [USER, search_output([CANVAS], "imported")]))
    content = at(standalone.body, "messages", 0, "content")
    assert isinstance(content, list)
    assert not any(isinstance(block, dict) and block.get("type") == "tool_result" for block in content)
    assert content[-1] == {"type": "text", "text": f"Loaded tools: {at(standalone.body, 'tools', 1, 'name')}"}


@pytest.mark.parametrize(
    "items,tools",
    [
        ([USER, {**search_call(), "arguments": '{"query":"canvas"}'}, search_output([])], [SEARCH_TOOL]),
        ([USER, search_call()], [SEARCH_TOOL]),
        ([USER], [{**SEARCH_TOOL, "execution": "server"}]),
        ([USER], [SEARCH_TOOL, SEARCH_TOOL]),
        ([USER, search_call(), {**search_output([]), "tools": None}], [SEARCH_TOOL]),
    ],
)
def test_malformed_search_history_and_declarations_are_rejected(items, tools):
    with pytest.raises(ClientPayloadError):
        project(request(tools, items))


def _codec() -> ClaudeOpaqueState:
    return ClaudeOpaqueState(TokenEncryptor(key=Fernet.generate_key()))


def test_claude_search_call_streams_as_a_held_client_tool_search_call_and_replays():
    projected = project(request([SEARCH_TOOL], [USER]))
    adapter = ResponsesProjection(
        OpaqueScope("source-a", "anthropic/claude-opus-5-5", "key-a"), projected.tools, _codec()
    )
    block = {"type": "tool_use", "id": "toolu_1", "name": "ToolSearch", "input": {}}
    events = adapter.consume({"type": "message_start", "message": {"id": "m", "usage": {}}})
    events += adapter.consume({"type": "content_block_start", "index": 0, "content_block": block})
    for fragment in ('{"query":', '"canvas"}'):
        events += adapter.consume(
            {"type": "content_block_delta", "index": 0, "delta": {"type": "input_json_delta", "partial_json": fragment}}
        )
    held = adapter.consume({"type": "content_block_stop", "index": 0})
    assert held == []  # Released only once the stop reason shows the turn was not refused.
    events += adapter.consume({"type": "message_delta", "delta": {"stop_reason": "tool_use"}, "usage": {}})
    events += adapter.consume({"type": "message_stop"})

    assert not [event for event in events if "arguments" in str(event["type"]) or "input" in str(event["type"])]
    added = next(event for event in events if event["type"] == "response.output_item.added")
    assert at(added, "item", "arguments") == {}
    item = at(events[-1], "response", "output", 0)
    assert item == {
        "id": "resp_m_0",
        "type": "tool_search_call",
        "call_id": "toolu_1",
        "execution": "client",
        "status": "completed",
        "arguments": {"query": "canvas"},
    }
    replay = project(request([SEARCH_TOOL], [USER, item, search_output([CANVAS], "toolu_1")]))
    assert at(replay.body, "messages", 1, "content", 0) == {
        "type": "tool_use",
        "id": "toolu_1",
        "name": "ToolSearch",
        "input": {"query": "canvas"},
    }


def test_tool_breakpoint_skips_deferred_tools():
    body: dict[str, JsonValue] = {
        "tools": [
            {"name": "ToolSearch", "input_schema": {"type": "object"}},
            {"name": "Canvas", "input_schema": {"type": "object"}, "defer_loading": True},
        ],
        "messages": [{"role": "user", "content": [{"type": "text", "text": "Hi"}]}],
    }
    cache_translated(body)
    assert "cache_control" in at(body, "tools", 0)
    assert "cache_control" not in at(body, "tools", 1)


def test_cache_miss_diagnostics_ignore_deferred_tool_loads(caplog: pytest.LogCaptureFixture):
    lineage = CacheLineage()
    base: dict[str, JsonValue] = {
        "model": "claude-opus-5-5",
        "tools": [{"name": "ToolSearch", "input_schema": {"type": "object"}}],
        "system": [{"type": "text", "text": "identity"}],
        "messages": [{"role": "user", "content": [{"type": "text", "text": "Hi"}]}],
    }
    lineage.observe(
        conversation_id="c", session_id=None, source_id="a", body=base, usage={"cache_read_input_tokens": 9}
    )
    loaded = {**base, "tools": [*base["tools"], {"name": "Canvas", "defer_loading": True}]}  # type: ignore[misc]
    with caplog.at_level(logging.INFO):
        lineage.observe(
            conversation_id="c",
            session_id=None,
            source_id="a",
            body=loaded,
            usage={"cache_read_input_tokens": 0, "cache_creation_input_tokens": 100_000},
        )
    [line] = [record.getMessage() for record in caplog.records if "claude_cache_miss" in record.getMessage()]
    assert "tools=same" in line
