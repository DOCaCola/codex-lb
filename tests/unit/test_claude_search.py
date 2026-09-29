import json
from copy import deepcopy

import pytest
from pydantic import JsonValue

from app.core.openai.exceptions import ClientPayloadError
from app.modules.claude.capabilities import reasoning_spec
from app.modules.claude.credentials import ClaudeError
from app.modules.claude.protocol import project_responses
from app.modules.claude.responses import ResponsesProjection
from tests.claude_json_helpers import at
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
    adapter = ResponsesProjection(scope(), {}, opaque, search_enabled=True)
    response = adapter.complete({"id": "search", "content": search_content(), "stop_reason": "end_turn"})
    assert at(response, "output", 0, "type") == "web_search_call"
    assert at(response, "output", 0, "status") == "completed"
    assert at(response, "output", 2, "content", 0, "annotations", 0, "start_index") == 3
    output = response["output"]
    assert isinstance(output, list)
    replay = project(
        request(input=[{"role": "user", "content": "Search"}, *output]),
        max_output_tokens=8192,
        restore_reasoning=lambda token: (
            opaque.decode(
                token,
                model=scope().model,
                client_scope=scope().client_scope,
                conversation_id=scope().conversation_id,
            ).block
        ),
    )
    restored = at(replay.body, "messages", 1, "content")
    assert isinstance(restored, list)
    assert restored[:2] == search_content()[:2]
    with pytest.raises(ClientPayloadError, match="opaque state"):
        project(request(input=[output[0]]), max_output_tokens=8192)


def test_stream_search_json_and_citation_deltas():
    adapter = ResponsesProjection(scope(), {}, codec(), search_enabled=True)
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


@pytest.mark.parametrize("changed", ["model", "client_scope", "conversation_id", "token"])
def test_search_state_rejects_changed_scope_or_tampering(changed):
    opaque = codec()
    response = ResponsesProjection(scope(), {}, opaque, search_enabled=True).complete(
        {"id": "search", "content": search_content(), "stop_reason": "end_turn"}
    )
    token = at(response, "output", 1, "encrypted_content")
    assert isinstance(token, str)
    arguments = {
        "model": scope().model,
        "client_scope": scope().client_scope,
        "conversation_id": scope().conversation_id,
    }
    if changed == "token":
        token = token[:30] + ("A" if token[30] != "A" else "B") + token[31:]
    else:
        arguments[changed] = "other"
    with pytest.raises(ClientPayloadError):
        opaque.decode(token, **arguments)


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
        ResponsesProjection(scope(), {}, codec(), search_enabled=True).complete(
            {"id": "search", "content": content, "stop_reason": "end_turn"}
        )
