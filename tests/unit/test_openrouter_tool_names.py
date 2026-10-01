import copy
import json
import re

import pytest

from app.core.utils.sse import parse_sse_data_json
from app.modules.openrouter.tool_names import ToolIdentity, ToolNames

pytestmark = pytest.mark.unit
NAMESPACE = "mcp__codex_apps__codex_document_control"
NAME = "execute_document_command"


def test_projection_identity_replay_choice_and_collision_domains():
    original = {
        "tools": [
            {"type": "namespace", "name": NAMESPACE, "tools": [{"type": "function", "name": NAME}]},
            {"type": "function", "name": "x" * 100},
            {"type": "function", "name": "read"},
        ],
        "tool_choice": {"type": "allowed_tools", "tools": [{"type": "function", "namespace": NAMESPACE, "name": NAME}]},
        "input": [{"type": "function_call", "namespace": NAMESPACE, "name": NAME, "arguments": NAME, "call_id": "one"}],
    }
    saved = copy.deepcopy(original)
    names = ToolNames()
    result = names.project(original, responses=True)
    alias = result["tools"][0]["name"]
    assert re.fullmatch(r"[A-Za-z0-9_-]{1,64}", alias)
    assert result["input"][0]["name"] == alias
    assert result["input"][0]["arguments"] == NAME
    assert result["tool_choice"]["tools"][0]["name"] == alias
    assert result["tools"][2]["name"] == "read"
    assert original == saved
    echoed = names.restore({"tools": copy.deepcopy(result["tools"]), "tool_choice": result["tool_choice"]})
    assert echoed == {"tools": saved["tools"], "tool_choice": saved["tool_choice"]}
    restored = names.restore({"output": result["input"]})
    assert restored["output"] == original["input"]
    assert ToolIdentity("a__b", "c").alias() != ToolIdentity("b", "c__a").alias()
    assert ToolIdentity(alias).alias() != alias
    reversed_result = ToolNames().project({"tools": list(reversed(original["tools"]))}, responses=True)
    assert reversed_result["tools"][-1]["name"] == alias
    historical = ToolNames().project({"input": original["input"]}, responses=True)
    assert historical["input"][0]["name"] == alias


@pytest.mark.parametrize("ending", ["\n\n", "\r\n\r\n", "\r\r"])
@pytest.mark.parametrize("chunk_size", [1, 7, 10000])
async def test_responses_stream_restores_item_terminal_and_preserves_text(ending, chunk_size):
    names = ToolNames()
    call = {"type": "custom_tool_call", "name": NAME, "namespace": NAMESPACE, "input": "héllo", "call_id": "call_one"}
    wire = names.project({"input": [call]}, responses=True)["input"][0]
    events = [
        {"type": "response.output_item.added", "item": wire},
        {"type": "response.custom_tool_call_input.done", "name": wire["name"], "input": "héllo"},
        {"type": "response.completed", "response": {"output": [wire]}},
    ]
    data = "".join("id: test\ndata: " + json.dumps(event, ensure_ascii=False) + ending for event in events).encode()
    closed = []

    async def body():
        try:
            for offset in range(0, len(data), chunk_size):
                yield data[offset : offset + chunk_size]
        finally:
            closed.append(True)

    blocks = [chunk.decode() async for chunk in names.restore_stream(body())]
    restored = [parse_sse_data_json(block) for block in blocks]
    assert restored[0]["item"] == call
    assert restored[1]["name"] == NAME
    assert restored[2]["response"]["output"] == [call]
    assert all("id: test" in block for block in blocks)
    assert closed == [True]


@pytest.mark.parametrize("openrouter", [True, False])
async def test_responses_stream_declares_plaintext_encrypted_parameter_calls(openrouter):
    payload = {
        "tools": [
            {
                "type": "namespace",
                "name": "collaboration",
                "tools": [
                    {
                        "type": "function",
                        "name": "spawn_agent",
                        "parameters": {"type": "object", "properties": {"message": {"encrypted": True}}},
                    }
                ],
            },
            {"type": "function", "name": "read", "parameters": {"type": "object", "properties": {}}},
        ]
    }
    names = ToolNames()
    names.declare_plaintext_arguments(payload)
    assert names.rewrites_output
    spawn = {
        "type": "function_call",
        "namespace": "collaboration",
        "name": "spawn_agent",
        "arguments": '{"message":"Go"}',
        "call_id": "a",
    }
    read = {"type": "function_call", "name": "read", "arguments": "{}", "call_id": "b"}
    if openrouter:
        projected = names.project({**payload, "input": [copy.deepcopy(spawn), copy.deepcopy(read)]}, responses=True)
        wire_spawn, wire_read = projected["input"]
    else:
        wire_spawn, wire_read = copy.deepcopy(spawn), copy.deepcopy(read)
    events = [
        {"type": "response.output_item.done", "item": wire_spawn},
        {"type": "response.completed", "response": {"output": [wire_spawn, wire_read]}},
    ]
    data = "".join("data: " + json.dumps(event) + "\n\n" for event in events).encode()

    async def body():
        yield data

    restored = [parse_sse_data_json(chunk.decode()) async for chunk in names.restore_stream(body())]
    marked = {**spawn, "encrypted_function_args": []}
    assert restored[0]["item"] == marked
    assert restored[1]["response"]["output"] == [marked, read]


async def test_chat_fragmented_alias_and_history():
    name = "mcp__" + "long_" * 20
    names = ToolNames()
    projected = names.project(
        {
            "tools": [{"type": "function", "function": {"name": name}}],
            "tool_choice": {"type": "function", "function": {"name": name}},
            "messages": [{"role": "assistant", "tool_calls": [{"type": "function", "function": {"name": name}}]}],
        },
        responses=False,
    )
    alias = projected["tools"][0]["function"]["name"]
    assert projected["messages"][0]["tool_calls"][0]["function"]["name"] == alias
    assert projected["tool_choice"]["function"]["name"] == alias
    events = [
        {"choices": [{"index": 0, "delta": {"tool_calls": [{"index": 0, "function": {"name": fragment}}]}}]}
        for fragment in (alias[:2], alias[2:19], alias[19:])
    ]

    async def body():
        for event in events:
            yield ("data: " + json.dumps(event) + "\n\n").encode()
        yield b"data: [DONE]\n\n"

    blocks = [chunk.decode() async for chunk in names.restore_stream(body())]
    decoded = [parse_sse_data_json(block) for block in blocks[:-1]]
    assert (
        "".join(event["choices"][0]["delta"]["tool_calls"][0]["function"].get("name", "") for event in decoded) == name
    )
    assert blocks[-1] == "data: [DONE]\n\n"
    complete = {"choices": [{"message": {"tool_calls": [{"function": {"name": alias, "arguments": alias}}]}}]}
    restored = names.restore(complete)["choices"][0]["message"]["tool_calls"][0]["function"]
    assert restored == {"name": name, "arguments": alias}


@pytest.mark.parametrize("last", ["arguments", "finish"])
def test_ordinary_name_sharing_alias_prefix_is_not_lost(last):
    names = ToolNames()
    names.project({"tools": [{"type": "function", "name": "x" * 100}]}, responses=True)
    first = names.restore(
        {"choices": [{"index": 0, "delta": {"tool_calls": [{"index": 0, "function": {"name": "l"}}]}}]}
    )
    assert "name" not in first["choices"][0]["delta"]["tool_calls"][0]["function"]
    final = (
        {"choices": [{"index": 0, "delta": {"tool_calls": [{"index": 0, "function": {"arguments": "{}"}}]}}]}
        if last == "arguments"
        else {"choices": [{"index": 0, "delta": {}, "finish_reason": "tool_calls"}]}
    )
    restored = names.restore(final)
    assert restored["choices"][0]["delta"]["tool_calls"][0]["function"]["name"] == "l"
    assert not names.fragments


async def test_stream_early_close_releases_body():
    names = ToolNames()
    names.project({"tools": [{"type": "function", "name": "x" * 100}]}, responses=True)
    closed = []

    async def body():
        try:
            yield b": heartbeat\n\n"
            yield b"data: [DONE]\n\n"
        finally:
            closed.append(True)

    stream = names.restore_stream(body())
    assert await anext(stream) == b": heartbeat\n\n"
    await stream.aclose()
    assert closed == [True]
