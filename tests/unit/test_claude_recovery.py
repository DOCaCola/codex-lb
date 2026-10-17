from copy import deepcopy

import pytest

from app.modules.claude.credentials import ClaudeError
from app.modules.claude.recovery import bind_replayed_thinking, historical_recovery
from app.modules.claude.wire_identity import native_conversation_id
from app.modules.model_sources.forwarding import ModelSourceForwardingError
from tests.claude_json_helpers import array, at

pytestmark = pytest.mark.unit


def failure(status=400, message="Invalid `signature` in `thinking` block"):
    return ModelSourceForwardingError(status_code=status, payload={"error": {"message": message}})


def history():
    return {
        "messages": [
            {"role": "user", "content": "hi"},
            {
                "role": "assistant",
                "content": [
                    {"type": "thinking", "thinking": "old", "signature": "opaque"},
                    {"type": "text", "text": "answer"},
                ],
            },
            {"role": "user", "content": "continue"},
        ],
        "thinking": {"type": "adaptive"},
    }


def test_recovery_preserves_visible_history_and_original():
    body = history()
    original = deepcopy(body)
    recovered = historical_recovery(body, failure(), readable_history=False)
    assert body == original
    assert recovered["messages"][1]["content"] == [{"type": "text", "text": "answer"}]
    assert recovered["thinking"] == body["thinking"]


def test_recovery_protects_the_open_tool_turn_behind_a_system_turn():
    body = history()
    body["messages"][2:] = [
        {"role": "user", "content": "run it"},
        {
            "role": "assistant",
            "content": [
                {"type": "thinking", "thinking": "plan", "signature": "open"},
                {"type": "tool_use", "id": "t1", "name": "shell", "input": {}},
            ],
        },
        {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t1", "content": "ok"}]},
        {"role": "system", "content": [{"type": "text", "text": "Sandbox changed"}]},
    ]
    recovered = historical_recovery(body, failure(), readable_history=False)
    assert recovered is not None
    assert at(recovered, "messages", 1, "content") == [{"type": "text", "text": "answer"}]
    assert array(at(recovered, "messages"))[3:] == body["messages"][3:]


def test_summarization_recovery_reads_historical_thinking():
    body = history()
    body["messages"][1]["content"].insert(1, {"type": "redacted_thinking", "data": "opaque"})
    original = deepcopy(body)
    recovered = historical_recovery(body, failure(), readable_history=True)
    assert body == original
    assert recovered is not None
    assert at(recovered, "messages", 1, "content") == [
        {"type": "text", "text": "old"},
        {"type": "text", "text": "answer"},
    ]
    body["messages"][1]["content"] = [{"type": "thinking", "thinking": "only", "signature": "opaque"}]
    recovered = historical_recovery(body, failure(), readable_history=True)
    assert recovered is not None
    assert at(recovered, "messages", 1, "content") == [{"type": "text", "text": "only"}]


@pytest.mark.parametrize(
    "status,message",
    [
        (429, "Invalid signature in thinking block"),
        (400, "thinking blocks in the latest assistant message cannot be modified"),
        (400, "Invalid request"),
        (500, "Invalid signature in thinking block"),
    ],
)
def test_unrelated_errors_do_not_recover(status, message):
    assert historical_recovery(history(), failure(status, message), readable_history=False) is None


def test_protects_complete_active_tool_chain():
    body = history()
    for i in range(3):
        body["messages"].extend(
            [
                {
                    "role": "assistant",
                    "content": [
                        {"type": "thinking", "thinking": "active", "signature": "sig"},
                        {"type": "tool_use", "id": str(i), "name": "read", "input": {}},
                    ],
                },
                {"role": "user", "content": [{"type": "tool_result", "tool_use_id": str(i), "content": "ok"}]},
            ]
        )
    for readable in (False, True):
        recovered = historical_recovery(body, failure(), readable_history=readable)
        assert recovered is not None
        assert array(recovered["messages"])[3:] == body["messages"][3:]


def test_empty_message_and_server_state_refuse_recovery():
    body = history()
    body["messages"][1]["content"].pop()
    assert historical_recovery(body, failure(), readable_history=False) is None
    body["messages"][1]["content"] = [{"type": "redacted_thinking", "data": "opaque"}]
    assert historical_recovery(body, failure(), readable_history=True) is None
    body = history()
    body["messages"][1]["content"].append({"type": "server_tool_use", "id": "search"})
    assert historical_recovery(body, failure(), readable_history=True) is None


@pytest.mark.parametrize(
    ("model", "thinking", "bound"),
    [
        ("claude-opus-5-5", {"type": "adaptive"}, True),
        ("claude-opus-5-5-20260901", {"type": "enabled", "budget_tokens": 4096}, True),
        ("claude-fable-5-1", {"type": "adaptive"}, True),
        ("claude-haiku-5-5", {"type": "adaptive"}, True),
        ("claude-haiku-5-5", {"type": "enabled", "budget_tokens": 4096}, False),
        ("claude-sonnet-5-5", {"type": "disabled"}, False),
        ("claude-opus-5", {"type": "adaptive"}, False),
    ],
)
def test_replayed_thinking_binding_follows_model_and_thinking_mode(model, thinking, bound):
    body = {**history(), "model": model, "thinking": thinking}
    assert bind_replayed_thinking(body) is bound
    assert ("block_binding" in body["thinking"]) is bound
    if bound:
        assert body["thinking"] == {**thinking, "block_binding": {"prefix_mismatch_behavior": "drop_block"}}


def test_replayed_thinking_binding_requires_signed_history_and_keeps_caller_choice():
    body = {**history(), "model": "claude-opus-5-5"}
    body["messages"][1]["content"][0]["signature"] = ""
    assert bind_replayed_thinking(body) is False
    body["messages"][1]["content"][0] = {"type": "redacted_thinking", "data": "opaque"}
    assert bind_replayed_thinking(body) is True
    chosen = {"type": "adaptive", "block_binding": {"prefix_mismatch_behavior": "error"}}
    body = {**history(), "model": "claude-opus-5-5", "thinking": chosen}
    assert bind_replayed_thinking(body) is False
    assert body["thinking"] == chosen


def test_explicit_identity_and_conflict():
    assert native_conversation_id({}, {"x-session-id": "thread"}) == "thread"
    with pytest.raises(ClaudeError, match="disagree"):
        native_conversation_id({}, {"x-session-id": "a", "x-claude-code-session-id": "b"})
    assert native_conversation_id({}, {"prompt_cache_key": "shared"}) != "shared"
