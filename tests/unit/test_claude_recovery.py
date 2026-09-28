from copy import deepcopy

import pytest

from app.modules.claude.credentials import ClaudeError
from app.modules.claude.recovery import historical_recovery
from app.modules.claude.wire_identity import native_conversation_id
from app.modules.model_sources.forwarding import ModelSourceForwardingError

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
    recovered = historical_recovery(body, failure())
    assert body == original
    assert recovered["messages"][1]["content"] == [{"type": "text", "text": "answer"}]
    assert recovered["thinking"] == body["thinking"]


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
    assert historical_recovery(history(), failure(status, message)) is None


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
    recovered = historical_recovery(body, failure())
    assert recovered["messages"][3:] == body["messages"][3:]


def test_empty_message_and_server_state_refuse_recovery():
    body = history()
    body["messages"][1]["content"].pop()
    assert historical_recovery(body, failure()) is None
    body = history()
    body["messages"][1]["content"].append({"type": "server_tool_use", "id": "search"})
    assert historical_recovery(body, failure()) is None


def test_explicit_identity_and_conflict():
    assert native_conversation_id({}, {"x-session-id": "thread"}) == "thread"
    with pytest.raises(ClaudeError, match="disagree"):
        native_conversation_id({}, {"x-session-id": "a", "x-claude-code-session-id": "b"})
    assert native_conversation_id({}, {"prompt_cache_key": "shared"}) != "shared"
