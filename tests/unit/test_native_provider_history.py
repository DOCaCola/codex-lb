from copy import deepcopy

import pytest
from pydantic import JsonValue

from app.core.openai.exceptions import ClientPayloadError
from app.core.openai.reasoning import ensure_native_provider_history
from app.core.openai.requests import ResponsesRequest, sanitize_native_responses_input
from app.modules.claude.replay import project_native_replay
from app.modules.proxy import service as proxy_service
from tests.unit.test_claude_protocol import codec, scope
from tests.unit.test_proxy_utils import _repo_factory, _RequestLogsRecorder

pytestmark = pytest.mark.unit


def reasoning(opaque, block=None):
    return {
        "id": "resp_msg_011CfZMoJxcBo6bvenx5qRj2_0",
        "type": "reasoning",
        "summary": [],
        "encrypted_content": opaque.encode(
            scope(), block or {"type": "thinking", "thinking": "Recovered Claude context", "signature": "signed"}
        ),
    }


def convert(items, opaque, **overrides):
    return project_native_replay(
        items,
        opaque,
        client_scope=overrides.get("client_scope", scope().client_scope),
    )


def test_empty_summary_envelope_is_recovered_without_mutating_tools_or_history():
    opaque = codec()
    items = [
        reasoning(opaque),
        {"type": "function_call", "call_id": "call_lookup", "name": "lookup", "arguments": "{}"},
        {"type": "function_call_output", "call_id": "call_lookup", "output": "result"},
        {"type": "custom_tool_call", "call_id": "call_patch", "name": "apply_patch", "input": "patch"},
        {"type": "custom_tool_call_output", "call_id": "call_patch", "output": "done"},
        {"type": "message", "role": "assistant", "content": "visible answer"},
    ]
    original = deepcopy(items)
    projected = convert(items, opaque)
    assert projected[0] == {
        "type": "reasoning",
        "summary": [{"type": "summary_text", "text": "Recovered Claude context"}],
    }
    assert projected[1:] == items[1:]
    assert items == original
    assert "signed" not in str(projected)
    ensure_native_provider_history({"input": projected})


def test_cross_client_projection_fails_without_mutation():
    opaque = codec()
    items = [reasoning(opaque)]
    original = deepcopy(items)
    with pytest.raises(ClientPayloadError) as raised:
        convert(items, opaque, client_scope="another")
    assert raised.value.code == "invalid_provider_history"
    assert raised.value.param == "input[0]"
    assert items == original


def test_tampered_envelope_is_not_stripped_or_forwarded():
    opaque = codec()
    items = [reasoning(opaque)]
    items[0]["encrypted_content"] = "claude-v1.invalid"
    with pytest.raises(ClientPayloadError, match="Invalid Claude reasoning state"):
        convert(items, opaque)


def search_state(opaque, item_id="resp_search_0"):
    from tests.unit.test_claude_search import search_content

    return reasoning(opaque, {"type": "web_search", "item_id": item_id, "blocks": search_content()[:2]})


def test_redacted_thinking_is_omitted_without_discarding_retained_history(caplog):
    opaque = codec()
    items = [reasoning(opaque), reasoning(opaque, {"type": "redacted_thinking", "data": "opaque"})]
    original = deepcopy(items)
    with caplog.at_level("INFO"):
        projected = convert(items, opaque)
    assert projected == [
        {"type": "reasoning", "summary": [{"type": "summary_text", "text": "Recovered Claude context"}]}
    ]
    assert items == original
    assert "converted=1 redacted_omitted=1 search_projected=0" in caplog.text


def test_hosted_search_becomes_readable_text_in_place_of_its_call():
    opaque = codec()
    items = [
        {
            "type": "web_search_call",
            "id": "resp_search_0",
            "status": "completed",
            "action": {"type": "search", "query": "test"},
        },
        search_state(opaque),
        {"type": "message", "role": "assistant", "content": "An answer"},
    ]
    original = deepcopy(items)
    projected = convert(items, opaque)
    assert projected == [
        {
            "type": "message",
            "role": "assistant",
            "content": [{"type": "output_text", "text": "Web search: test\nSources:\n- Example — https://example.com"}],
        },
        items[2],
    ]
    assert "upstream-owned-opaque-data" not in str(projected)
    assert items == original
    ensure_native_provider_history({"input": projected})


def test_search_state_without_its_call_fails():
    opaque = codec()
    with pytest.raises(ClientPayloadError) as raised:
        convert([reasoning(opaque), search_state(opaque)], opaque)
    assert raised.value.code == "invalid_provider_history"
    assert raised.value.param == "input[1]"


@pytest.mark.parametrize(
    ("action", "text"),
    [
        ({"type": "search", "query": "weather"}, "Web search: weather"),
        ({"type": "search", "queries": ["a", "b"]}, "Web search: a; b"),
        (
            {"type": "search", "query": "weather", "sources": [{"type": "url", "url": "https://w.example"}]},
            "Web search: weather\nSources:\n- https://w.example",
        ),
        ({"type": "open_page", "url": "https://w.example"}, "Opened page: https://w.example"),
        (
            {"type": "find_in_page", "url": "https://w.example", "pattern": "rain"},
            "Found in page https://w.example: rain",
        ),
        ({"type": "other"}, "Web search"),
        (None, "Web search"),
    ],
)
def test_openai_search_text(action, text):
    from app.modules.claude.search import openai_search_text

    item: dict[str, JsonValue] = {"type": "web_search_call", "id": "ws_1"}
    if action is not None:
        item["action"] = action
    assert openai_search_text(item) == text


def test_native_sanitation_preserves_all_distinct_plaintext_and_native_encryption():
    items: list[JsonValue] = [
        {
            "id": "rs_native",
            "type": "reasoning",
            "summary": [{"type": "summary_text", "text": "Existing summary"}],
            "content": [
                {"type": "reasoning_text", "text": "Additional thought"},
                {"type": "reasoning_text", "text": "Additional thought"},
            ],
            "encrypted_content": "native-opaque",
            "status": "completed",
        },
        {"type": "reasoning", "id": "resp_msg_foreign", "summary": [], "encrypted_content": "native-opaque"},
        {"type": "item_reference", "id": "msg_stored"},
    ]
    payload: dict[str, JsonValue] = {"store": False, "input": items}
    original = deepcopy(payload)
    result = sanitize_native_responses_input(payload)
    assert result["input"] == [
        {
            "id": "rs_native",
            "type": "reasoning",
            "summary": [
                {"type": "summary_text", "text": "Existing summary"},
                {"type": "summary_text", "text": "Additional thought"},
            ],
            "content": [],
            "encrypted_content": "native-opaque",
        },
        {"type": "reasoning", "summary": [], "encrypted_content": "native-opaque"},
        {"type": "item_reference", "id": "msg_stored"},
    ]
    assert payload == original


@pytest.mark.parametrize("store", [False, True])
def test_invalid_item_prefixes_are_removed_independently_of_store(store):
    payload: dict[str, JsonValue] = {
        "store": store,
        "input": [
            {"type": kind, "id": "resp_msg_foreign", "encrypted_content": "opaque"}
            for kind in ("message", "reasoning", "function_call", "custom_tool_call", "web_search_call")
        ],
    }
    result = sanitize_native_responses_input(payload)
    assert all("id" not in item for item in result["input"])
    assert all("id" in item for item in payload["input"])


def test_low_level_native_boundary_rejects_unprojected_envelope():
    opaque = codec()
    with pytest.raises(ClientPayloadError) as raised:
        ensure_native_provider_history({"input": [reasoning(opaque)]})
    assert raised.value.code == "nonportable_provider_history"


def test_native_frame_serializer_rejects_unprojected_envelope():
    payload = ResponsesRequest.model_validate(
        {"model": "gpt-6.1-sol", "instructions": "Continue", "input": [reasoning(codec())]}
    )
    with pytest.raises(ClientPayloadError, match="authenticated projection"):
        proxy_service._response_create_text(payload, include_type_field=True, client_metadata=None)


def test_nontext_reasoning_is_rejected_instead_of_discarded():
    payload = {"input": [{"type": "reasoning", "content": [{"type": "unknown", "data": "retained"}]}]}
    original = deepcopy(payload)
    with pytest.raises(ClientPayloadError) as raised:
        sanitize_native_responses_input(payload)
    assert raised.value.param == "input[0].content"
    assert payload == original


@pytest.mark.parametrize("transport", ["http", "websocket"])
def test_native_serializers_preserve_recovered_history(transport):
    import json

    opaque = codec()
    payload = ResponsesRequest.model_validate(
        {
            "model": "gpt-6.1-sol",
            "instructions": "Continue",
            "input": convert([reasoning(opaque)], opaque),
            "stream": True,
        }
    )
    service = proxy_service.ProxyService(_repo_factory(_RequestLogsRecorder()))
    state, prepared = service._prepare_response_bridge_request_state(
        payload,
        api_key=None,
        api_key_reservation=None,
        include_type_field=True,
        attach_event_queue=False,
        transport=transport,
        client_metadata=None,
    )
    replay = proxy_service._response_create_text_with_size_guard(
        payload, include_type_field=True, client_metadata=None, request_state=state, transport=transport
    )
    assert json.loads(prepared)["input"] == json.loads(replay)["input"] == payload.input
