from copy import deepcopy

import pytest

from app.core.openai.exceptions import ClientPayloadError
from app.modules.claude.protocol import project_responses
from app.modules.claude.replay import authenticate_replay, project_foreign_replay
from tests.claude_json_helpers import array, at
from tests.unit.test_claude_protocol import TASK_INPUT, codec, scope

pytestmark = pytest.mark.unit


def history(*, token="gAAAA_native_openai", summary="Sol context", content="Distinct raw context", completed=True):
    item = {"type": "reasoning", "id": "rs_native", "summary": [], "content": []}
    if token is not None:
        item["encrypted_content"] = token
    if summary is not None:
        item["summary"] = [{"type": "summary_text", "text": summary}]
    if content is not None:
        item["content"] = [{"type": "reasoning_text", "text": content}]
    items = [{"role": "user", "content": "Original request"}, item]
    items.extend(
        [
            {"type": "function_call", "call_id": "call_native", "name": "lookup", "arguments": "{}"},
            {"type": "function_call_output", "call_id": "call_native", "output": "result"},
        ]
    )
    if completed:
        items.append({"role": "user", "content": "Continue on Opus"})
    return {"model": scope().model, "input": items}


def test_historical_foreign_reasoning_becomes_text_without_mutating_tools_or_history(caplog):
    payload = history()
    original = deepcopy(payload)
    with caplog.at_level("INFO"):
        projected = project_foreign_replay(payload)
    assert at(projected["input"], 1) == {
        "type": "message",
        "role": "assistant",
        "content": [
            {"type": "output_text", "text": "Sol context"},
            {"type": "output_text", "text": "Distinct raw context"},
        ],
    }
    assert array(projected["input"])[2:] == payload["input"][2:]
    assert "gAAAA" not in str(projected) and "rs_native" not in str(projected)
    assert "converted=1" in caplog.text
    assert "Sol context" not in caplog.text and "gAAAA" not in caplog.text
    assert payload == original


def test_mirrored_summary_and_content_are_not_duplicated():
    projected = project_foreign_replay(history(content="Sol context"))
    assert at(projected["input"], 1, "content") == [{"type": "output_text", "text": "Sol context"}]


@pytest.mark.parametrize("summary,content", [(None, "raw only"), ("summary only", None), ("", "raw only")])
def test_readable_reasoning_channels_are_preserved(summary, content):
    projected = project_foreign_replay(history(summary=summary, content=content))
    assert at(projected["input"], 1, "content") == [{"type": "output_text", "text": summary or content}]


@pytest.mark.parametrize("summary,content", [(None, None), ("", ""), (" \t", "\n")])
def test_completed_opaque_only_state_has_no_wire_block_but_keeps_original_history(summary, content, caplog):
    payload = history(summary=summary, content=content)
    original = deepcopy(payload)
    with caplog.at_level("INFO"):
        projected = project_foreign_replay(payload)
    assert at(projected["input"], 1) == {"type": "reasoning", "summary": []}
    assert array(projected["input"])[2:] == payload["input"][2:]
    body = project_responses(projected, max_output_tokens=64000, reasoning=None).body
    assert "gAAAA" not in str(body) and "rs_native" not in str(body)
    assert "Original request" in str(body) and "Continue on Opus" in str(body)
    assert "call_native" in str(body) and "result" in str(body)
    assert "thinking" not in str(body)
    assert "converted=0 omitted=1" in caplog.text
    assert "gAAAA" not in caplog.text and "rs_native" not in caplog.text
    assert payload == original


@pytest.mark.parametrize("complete,completed", [(False, False), (True, True), (True, False)])
@pytest.mark.parametrize("readable", [False, True])
def test_foreign_encrypted_active_and_complete_history_fail(complete, completed, readable):
    payload = history(completed=completed) if readable else history(completed=completed, summary=None, content=None)
    with pytest.raises(ClientPayloadError) as error:
        project_foreign_replay(payload, require_complete_history=complete)
    assert error.value.code == "nonportable_provider_history"
    assert error.value.param == "input[1]"


@pytest.mark.parametrize("readable", [False, True])
def test_canonical_external_task_closes_foreign_history_but_tool_results_do_not(readable):
    payload = history(completed=False) if readable else history(completed=False, summary=None, content=None)
    with pytest.raises(ClientPayloadError, match="Active reasoning"):
        project_foreign_replay(payload)
    payload["input"].append(TASK_INPUT)
    projected = project_foreign_replay(payload)
    if readable:
        assert at(projected["input"], 1, "role") == "assistant"
    else:
        assert at(projected["input"], 1) == {"type": "reasoning", "summary": []}


@pytest.mark.parametrize("complete", [False, True])
def test_plaintext_only_history_needs_no_provider_signature_even_for_compaction(complete):
    payload = history(token=None, completed=False)
    projected = project_foreign_replay(payload, require_complete_history=complete)
    assert at(projected["input"], 1, "content", 0, "text") == "Sol context"


@pytest.mark.parametrize(
    "field,parts",
    [
        ("summary", {}),
        ("summary", [{"type": "summary_text", "text": 2}]),
        ("content", [{"type": "input_image", "image_url": "data:..."}]),
    ],
)
@pytest.mark.parametrize("token", [None, "gAAAA_native_openai"])
def test_unrepresentable_readable_state_is_not_discarded(field, parts, token):
    payload = history(token=token)
    payload["input"][1][field] = parts
    with pytest.raises(ClientPayloadError) as error:
        project_foreign_replay(payload)
    assert error.value.param == f"input[1].{field}"


@pytest.mark.parametrize("kind", ["thinking", "redacted_thinking"])
def test_genuine_empty_display_signed_blocks_remain_verbatim(kind):
    opaque = codec()
    block = {"type": kind, "thinking": "", "signature": "genuine", "data": "redacted"}
    token = opaque.encode(scope(), block)
    payload = history(token=token, summary=None, content=None, completed=False)
    assert project_foreign_replay(payload) is payload
    replay = authenticate_replay(payload, opaque, model=scope().model, client_scope="key-a", conversation_id="thread-a")
    assert replay.blocks[0].envelope.block == block
    assert replay.owner_source_id == "source-a"


@pytest.mark.parametrize("scope_field", ["client_scope", "conversation_id", "tampering"])
def test_projection_never_bypasses_authentication_including_forked_scope(scope_field):
    opaque = codec()
    token = opaque.encode(scope(), {"type": "thinking", "thinking": "", "signature": "signed"})
    payload = history(token=token if scope_field != "tampering" else "claude-v1.invalid")
    projected = project_foreign_replay(payload)
    with pytest.raises(ClientPayloadError) as error:
        authenticate_replay(
            projected,
            opaque,
            model=scope().model,
            client_scope="child-key" if scope_field == "client_scope" else "key-a",
            conversation_id="child-thread" if scope_field == "conversation_id" else "thread-a",
        )
    assert error.value.code == "invalid_provider_history"
    assert error.value.param == "input[1]"


@pytest.mark.parametrize("readable", [False, True])
def test_opus_sol_opus_mixed_history_keeps_original_signed_state(readable):
    opaque = codec()
    signed = {"type": "thinking", "thinking": "Original Opus context", "signature": "original-signature"}
    token = opaque.encode(scope(), signed)
    payload = history() if readable else history(summary=None, content=None)
    payload["input"].insert(0, {"type": "reasoning", "encrypted_content": token})
    projected = project_foreign_replay(payload)
    replay = authenticate_replay(
        projected, opaque, model=scope().model, client_scope="key-a", conversation_id="thread-a"
    )
    projected = replay.project(projected, source_id="source-a", model=scope().model)
    body = project_responses(
        projected,
        max_output_tokens=64000,
        reasoning=None,
        restore_reasoning=lambda value: (
            opaque.decode(value, model=scope().model, client_scope="key-a", conversation_id="thread-a").block
        ),
    ).body
    assert at(body["messages"], 0, "content") == [signed]
    assert ("Sol context" in str(body)) is readable
    assert "gAAAA" not in str(body)


@pytest.mark.parametrize("token", [None, "gAAAA_native_openai"])
def test_empty_projection_preserves_later_authentication_error_index(token):
    payload = history(token=token, summary=None, content=None)
    payload["input"].append({"type": "reasoning", "encrypted_content": "claude-v1.invalid"})
    projected = project_foreign_replay(payload)
    assert at(projected["input"], 1) == {"type": "reasoning", "summary": []}
    with pytest.raises(ClientPayloadError) as error:
        authenticate_replay(projected, codec(), model=scope().model, client_scope="key-a", conversation_id="thread-a")
    assert error.value.code == "invalid_provider_history"
    assert error.value.param == "input[5]"
