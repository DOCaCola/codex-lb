import json
from copy import deepcopy

import pytest
from pydantic import JsonValue

from app.core.openai.exceptions import ClientPayloadError
from app.modules.claude.capabilities import reasoning_spec
from app.modules.claude.credentials import ClaudeError
from app.modules.claude.protocol import project_responses
from app.modules.claude.responses import ResponsesProjection
from app.modules.claude.tool_names import ClaudeToolNames
from tests.claude_json_helpers import array, at
from tests.unit.test_claude_protocol import codec, request, scope

pytestmark = pytest.mark.unit


def project(payload, **kwargs):
    """Project with the policy-derived reasoning the payload's model would get."""
    return project_responses(payload, reasoning=reasoning_spec(str(payload.get("model", "")), None), **kwargs)


def search_content() -> list[JsonValue]:
    return [
        {"type": "server_tool_use", "id": "srvtoolu_search", "name": "web_search", "input": {"query": "test"}},
        {
            "type": "web_search_tool_result",
            "tool_use_id": "srvtoolu_search",
            "content": [
                {
                    "type": "web_search_result",
                    "url": "https://example.com",
                    "title": "Example",
                    "encrypted_content": "upstream-owned-opaque-data",
                    "page_age": "today",
                },
            ],
        },
        {
            "type": "text",
            "text": "An answer",
            "citations": [
                {
                    "type": "web_search_result_location",
                    "url": "https://example.com",
                    "title": "Example",
                    "encrypted_index": "upstream-index",
                    "cited_text": "answer",
                },
            ],
        },
    ]


@pytest.mark.parametrize("kind", ["web_search", "web_search_preview"])
def test_cached_only_search_is_omitted_without_mutating_caller(kind):
    payload = request(tools=[{"type": kind, "external_web_access": False}])
    original = deepcopy(payload)
    projected = project(payload, max_output_tokens=8192)
    assert "tools" not in projected.body
    assert not projected.search_enabled
    assert payload == original


def test_live_search_declaration_and_constraints():
    projected = project(
        request(
            tools=[
                {
                    "type": "web_search",
                    "filters": {"allowed_domains": ["example.com"]},
                    "user_location": {"type": "approximate", "country": "DE"},
                    "max_uses": 2,
                }
            ]
        ),
        max_output_tokens=8192,
    )
    assert at(projected.body, "tools", 0) == {
        "type": "web_search_20250305",
        "name": "web_search",
        "allowed_domains": ["example.com"],
        "user_location": {"type": "approximate", "country": "DE"},
        "max_uses": 2,
    }
    assert projected.search_enabled


@pytest.mark.parametrize(
    "option",
    [
        {"external_web_access": "false"},
        {"search_context_size": "low"},
        {"max_uses": True},
        {"filters": {"blocked_domains": ["example.com"]}},
        {"user_location": {"type": "precise"}},
    ],
)
def test_unsupported_live_options_fail_explicitly(option):
    with pytest.raises(ClientPayloadError):
        project(request(tools=[{"type": "web_search", **option}]), max_output_tokens=8192)


def test_search_lifecycle_citations_and_authenticated_replay():
    opaque = codec()
    adapter = ResponsesProjection(scope(), ClaudeToolNames(), opaque, search_enabled=True)
    response = adapter.complete({"id": "search", "content": search_content(), "stop_reason": "end_turn"})
    assert at(response, "output", 0, "type") == "web_search_call"
    assert at(response, "output", 0, "status") == "completed"
    assert at(response, "output", 2, "content", 0, "annotations", 0, "start_index") == 3
    output = response["output"]
    assert isinstance(output, list)
    replay = project(
        request(input=[{"role": "user", "content": "Search"}, *output]),
        max_output_tokens=8192,
        restore_reasoning=lambda token: opaque.authenticate(token, client_scope=scope().client_scope).block,
    )
    restored = at(replay.body, "messages", 1, "content")
    assert isinstance(restored, list)
    assert restored[:2] == search_content()[:2]
    with pytest.raises(ClientPayloadError, match="opaque state"):
        project(request(input=[output[0]]), max_output_tokens=8192)


def test_stream_search_json_and_citation_deltas():
    adapter = ResponsesProjection(scope(), ClaudeToolNames(), codec(), search_enabled=True)
    events = adapter.consume({"type": "message_start", "message": {"id": "search"}})
    for index, original in enumerate(search_content()):
        block = deepcopy(original)
        assert isinstance(block, dict)
        if index == 0:
            block["input"] = {}
        if index == 2:
            block["citations"] = []
        events += adapter.consume({"type": "content_block_start", "index": index, "content_block": block})
        if index == 0:
            for piece in ['{"query":', '"test"}']:
                events += adapter.consume(
                    {
                        "type": "content_block_delta",
                        "index": index,
                        "delta": {"type": "input_json_delta", "partial_json": piece},
                    }
                )
        if index == 2:
            events += adapter.consume(
                {
                    "type": "content_block_delta",
                    "index": index,
                    "delta": {"type": "citations_delta", "citation": at(original, "citations", 0)},
                }
            )
        events += adapter.consume({"type": "content_block_stop", "index": index})
    adapter.consume({"type": "message_delta", "delta": {"stop_reason": "end_turn"}})
    events += adapter.consume({"type": "message_stop"})
    kinds = [event["type"] for event in events]
    assert [k for k in kinds if isinstance(k, str) and k.startswith("response.web_search_call.")] == [
        "response.web_search_call.in_progress",
        "response.web_search_call.searching",
        "response.web_search_call.completed",
    ]
    assert "response.function_call_arguments.delta" not in kinds
    assert "response.output_text.annotation.added" in kinds
    assert kinds[-1] == "response.completed"
    assert "upstream-owned-opaque-data" not in json.dumps(events)


@pytest.mark.parametrize("changed", ["client_scope", "token"])
def test_search_state_rejects_changed_scope_or_tampering(changed):
    opaque = codec()
    response = ResponsesProjection(scope(), ClaudeToolNames(), opaque, search_enabled=True).complete(
        {"id": "search", "content": search_content(), "stop_reason": "end_turn"}
    )
    token = at(response, "output", 1, "encrypted_content")
    assert isinstance(token, str)
    client_scope = scope().client_scope
    if changed == "token":
        token = token[:30] + ("A" if token[30] != "A" else "B") + token[31:]
    else:
        client_scope = "other"
    with pytest.raises(ClientPayloadError):
        opaque.authenticate(token, client_scope=client_scope)


@pytest.mark.parametrize(
    "content",
    [
        search_content()[:1],
        [search_content()[1]],
        [
            search_content()[0],
            {
                "type": "web_search_tool_result",
                "tool_use_id": "srvtoolu_search",
                "content": {"type": "web_search_tool_result_error", "error_code": "unavailable"},
            },
        ],
    ],
)
def test_search_failure_never_becomes_success(content):
    with pytest.raises(ClaudeError):
        ResponsesProjection(scope(), ClaudeToolNames(), codec(), search_enabled=True).complete(
            {"id": "search", "content": content, "stop_reason": "end_turn"}
        )


LOOKUP = {"type": "function", "name": "lookup", "parameters": {"type": "object", "properties": {}}}


def deferred_turn(**overrides):
    """Search deferred beside a client call, its result and the client's tool output (Anthropic server tools docs)."""
    opaque = codec()
    declared = project(request(tools=[LOOKUP, {"type": "web_search"}]), max_output_tokens=8192)
    wire = at(declared.body, "tools", 0, "name")
    adapter = ResponsesProjection(scope(), declared.tools, opaque, search_enabled=True)
    call = search_content()[0]
    tool_use = {"type": "tool_use", "id": "toolu_lookup", "name": wire, "input": {}}
    response = adapter.complete({"id": "deferred", "content": [call, tool_use], "stop_reason": "tool_use", **overrides})
    return opaque, declared, response


def replay(opaque, items, tools=(LOOKUP, {"type": "web_search"})):
    return project(
        request(input=items, tools=list(tools)),
        max_output_tokens=8192,
        restore_reasoning=lambda token: opaque.authenticate(token, client_scope=scope().client_scope).block,
    )


def test_search_deferred_beside_a_client_call_completes_with_call_only_state(caplog):
    with caplog.at_level("INFO"):
        opaque, _, response = deferred_turn()
    assert response["status"] == "completed"
    output = response["output"]
    assert isinstance(output, list)
    assert [at(item, "type") for item in output] == ["web_search_call", "function_call", "reasoning"]
    assert at(output, 0, "status") == "in_progress"
    token = at(output, 2, "encrypted_content")
    assert isinstance(token, str)
    state = opaque.authenticate(token, client_scope=scope().client_scope).block
    assert state == {"type": "web_search", "item_id": at(output, 0, "id"), "blocks": search_content()[:1]}
    assert "pending_search=0 deferred_search=1" in caplog.text


def test_search_pending_without_a_client_call_still_fails():
    with pytest.raises(ClaudeError, match="pending_search=1, stop_reason=tool_use"):
        ResponsesProjection(scope(), ClaudeToolNames(), codec(), search_enabled=True).complete(
            {"id": "search", "content": search_content()[:1], "stop_reason": "tool_use"}
        )


def test_streamed_deferral_closes_search_after_the_held_call():
    declared = project(request(tools=[LOOKUP, {"type": "web_search"}]), max_output_tokens=8192)
    wire = at(declared.body, "tools", 0, "name")
    adapter = ResponsesProjection(scope(), declared.tools, codec(), search_enabled=True)
    events = adapter.consume({"type": "message_start", "message": {"id": "deferred"}})
    blocks = [search_content()[0], {"type": "tool_use", "id": "toolu_lookup", "name": wire, "input": {}}]
    for index, block in enumerate(blocks):
        events += adapter.consume({"type": "content_block_start", "index": index, "content_block": block})
        events += adapter.consume({"type": "content_block_stop", "index": index})
    events += adapter.consume({"type": "message_delta", "delta": {"stop_reason": "tool_use"}})
    events += adapter.consume({"type": "message_stop"})
    done = [at(event, "item", "type") for event in events if event["type"] == "response.output_item.done"]
    assert done == ["function_call", "web_search_call", "reasoning"]
    sequence: list[int] = []
    for event in events:
        number = event["sequence_number"]
        assert isinstance(number, int)
        sequence.append(number)
    assert sequence == sorted(sequence) and len(set(sequence)) == len(sequence)
    assert events[-1]["type"] == "response.completed"


def test_deferred_search_resumes_and_its_result_is_stored_as_a_pair():
    opaque, declared, response = deferred_turn()
    output = response["output"]
    assert isinstance(output, list)
    # Streamed clients record the held client call before the deferred search and its state.
    turn = [
        {"role": "user", "content": "Search and look up"},
        output[1],
        output[0],
        output[2],
        {"type": "function_call_output", "call_id": "toolu_lookup", "output": "found"},
    ]
    resumed = replay(opaque, turn)
    assert at(resumed.body, "messages", 1, "content") == [
        search_content()[0],
        at(resumed.body, "messages", 1, "content", 1),
    ]
    assert at(resumed.body, "messages", 1, "content", 1, "type") == "tool_use"
    assert [at(block, "type") for block in array(at(resumed.body, "messages", 2, "content"))] == ["tool_result"]
    assert resumed.deferred_searches == {"srvtoolu_search": (at(output, 0, "id"), search_content()[0])}

    adapter = ResponsesProjection(
        scope(), declared.tools, opaque, search_enabled=True, deferred_searches=resumed.deferred_searches
    )
    answer = adapter.complete({"id": "resumed", "content": search_content()[1:], "stop_reason": "end_turn"})
    answer_output = answer["output"]
    assert isinstance(answer_output, list)
    assert [at(item, "type") for item in answer_output] == ["reasoning", "message"]
    token = at(answer_output, 0, "encrypted_content")
    assert isinstance(token, str)
    assert opaque.authenticate(token, client_scope=scope().client_scope).block == {
        "type": "web_search",
        "item_id": at(output, 0, "id"),
        "blocks": search_content()[:2],
    }

    later = replay(opaque, [*turn, *answer_output, {"role": "user", "content": "Thanks"}])
    assert at(later.body, "messages", 1, "content", 0) == search_content()[0]
    assert at(later.body, "messages", 3, "content", 0) == search_content()[1]
    assert later.deferred_searches == {}


def test_result_without_a_call_or_resumable_deferral_fails():
    with pytest.raises(ClaudeError, match="no matching server call"):
        ResponsesProjection(
            scope(), ClaudeToolNames(), codec(), search_enabled=True, deferred_searches={"srvtoolu_other": ("x", {})}
        ).complete({"id": "resumed", "content": search_content()[1:], "stop_reason": "end_turn"})


@pytest.mark.parametrize(
    "reason,tail,tools",
    [
        ("search_undeclared", [], (LOOKUP,)),
        ("extra_content", [{"role": "user", "content": "Stop searching"}], (LOOKUP, {"type": "web_search"})),
        (
            "later_history",
            [{"role": "assistant", "content": "Stopped"}, {"role": "user", "content": "Next"}],
            (LOOKUP, {"type": "web_search"}),
        ),
    ],
)
def test_deferred_search_that_can_no_longer_run_is_omitted(caplog, reason, tail, tools):
    opaque, _, response = deferred_turn()
    output = response["output"]
    assert isinstance(output, list)
    items = [
        {"role": "user", "content": "Search and look up"},
        *output,
        {"type": "function_call_output", "call_id": "toolu_lookup", "output": "aborted"},
        *tail,
    ]
    with caplog.at_level("INFO"):
        projected = replay(opaque, items, tools)
    assert [at(block, "type") for block in array(at(projected.body, "messages", 1, "content"))] == ["tool_use"]
    assert projected.deferred_searches == {}
    assert f"claude_deferred_search_omitted request_id=None reasons={reason}:1" in caplog.text
