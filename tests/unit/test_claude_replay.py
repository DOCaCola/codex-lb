from copy import deepcopy

import pytest

from app.core.openai.exceptions import ClientPayloadError
from app.modules.claude.opaque import OpaqueScope
from app.modules.claude.replay import authenticate_replay
from app.modules.model_sources.compaction import source_compaction_instruction
from tests.unit.test_claude_protocol import TASK_INPUT, codec, scope

pytestmark = pytest.mark.unit


def history(opaque, *, kind="thinking", completed=True):
    token = opaque.encode(scope(), {"type": kind, "thinking": "private", "signature": "signed"})
    items = [{"type": "reasoning", "encrypted_content": token}, {"role": "assistant", "content": "answer"}]
    if completed:
        items.append({"role": "user", "content": "next"})
    return {"input": items}


def read(payload, opaque, *, require_complete_history=False, **overrides):
    return authenticate_replay(
        payload,
        opaque,
        model=overrides.get("model", scope().model),
        client_scope=overrides.get("client_scope", "key-a"),
        require_complete_history=require_complete_history,
    )


def compact(payload):
    return {**payload, "input": [*payload["input"], source_compaction_instruction()]}


READABLE = {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "private"}]}
SEARCH_TEXT = {
    "type": "message",
    "role": "assistant",
    "content": [{"type": "output_text", "text": "Web search: test\nSources:\n- Example — https://example.com"}],
}
SEARCH_CALL = {
    "type": "web_search_call",
    "id": "resp_search_0",
    "status": "completed",
    "action": {"type": "search", "query": "test"},
}


def search_history(opaque, *, completed=True):
    from tests.unit.test_claude_search import search_content

    token = opaque.encode(scope(), {"type": "web_search", "item_id": "resp_search_0", "blocks": search_content()[:2]})
    items = [SEARCH_CALL, {"type": "reasoning", "encrypted_content": token}, {"role": "assistant", "content": "answer"}]
    if completed:
        items.append({"role": "user", "content": "next"})
    return {"input": items}


@pytest.mark.parametrize("kind", ["thinking", "redacted_thinking"])
@pytest.mark.parametrize("completed", [True, False], ids=["completed", "active"])
def test_signed_thinking_moves_unchanged_and_projection_is_immutable(kind, completed):
    opaque = codec()
    payload = history(opaque, kind=kind, completed=completed)
    original = deepcopy(payload)
    replay = read(payload, opaque)
    assert replay.owner_source_id is None
    assert replay.preferred_source_id == "source-a"
    assert replay.project(payload, source_id="source-a", model=scope().model) == payload
    assert replay.project(payload, source_id="source-b", model=scope().model) == payload
    switched = read(payload, opaque, model="other")
    assert switched.preferred_source_id == "source-a"
    assert switched.project(payload, source_id="source-b", model="other") == payload
    assert payload == original


def test_active_search_cannot_move():
    opaque = codec()
    payload = search_history(opaque, completed=False)
    replay = read(payload, opaque)
    assert replay.owner_source_id == "source-a"
    with pytest.raises(ClientPayloadError, match="original account and model") as moved:
        replay.project(payload, source_id="source-b", model=scope().model)
    assert (moved.value.code, moved.value.param) == ("nonportable_provider_history", "input[1]")
    with pytest.raises(ClientPayloadError, match="original model") as switched:
        read(payload, opaque, model="other")
    assert (switched.value.code, switched.value.param) == ("nonportable_provider_history", "input[1]")


@pytest.mark.parametrize("compaction", [False, True])
def test_completed_search_moves_as_readable_text(caplog, compaction):
    opaque = codec()
    payload = search_history(opaque)
    if compaction:
        payload = compact(payload)
    original = deepcopy(payload)
    replay = read(payload, opaque, require_complete_history=compaction)
    assert replay.owner_source_id is None
    assert replay.preferred_source_id == "source-a"
    assert replay.project(payload, source_id="source-a", model=scope().model) == payload
    with caplog.at_level("INFO"):
        moved = replay.project(payload, source_id="source-b", model=scope().model)["input"]
    assert moved == [SEARCH_TEXT, *payload["input"][2:]]
    assert "converted=0 omitted=0 search_projected=1" in caplog.text
    switched = read(payload, opaque, model="other", require_complete_history=compaction)
    assert switched.project(payload, source_id="source-a", model="other")["input"] == moved
    assert payload == original


@pytest.mark.parametrize("completed", [True, False])
def test_foreign_search_becomes_readable_text_in_any_turn(completed):
    native = {**SEARCH_CALL, "id": "ws_native"}
    payload = {"input": [{"role": "user", "content": "look it up"}, native, {"role": "assistant", "content": "answer"}]}
    if completed:
        payload["input"].append({"role": "user", "content": "next"})
    original = deepcopy(payload)
    projected = read(payload, codec()).project(payload, source_id="source-a", model=scope().model)["input"]
    text = {**SEARCH_TEXT, "content": [{"type": "output_text", "text": "Web search: test"}]}
    assert projected == [payload["input"][0], text, *payload["input"][2:]]
    assert payload == original


def test_moved_search_state_without_its_call_fails():
    opaque = codec()
    payload = search_history(opaque)
    del payload["input"][0]
    with pytest.raises(ClientPayloadError, match="no matching search item"):
        read(payload, opaque).project(payload, source_id="source-b", model=scope().model)


def test_authentication_precedes_omission():
    opaque = codec()
    with pytest.raises(ClientPayloadError, match="another client") as rejected:
        read(history(opaque), opaque, client_scope="other")
    assert (rejected.value.code, rejected.value.param) == ("invalid_provider_history", "input[0]")


def test_mixed_completed_owners_are_not_conflicting():
    opaque = codec()
    payload = history(opaque)
    other = opaque.encode(OpaqueScope("source-b", scope().model, "key-a"), {"type": "thinking"})
    payload["input"].insert(1, {"type": "reasoning", "encrypted_content": other})
    replay = read(payload, opaque)
    assert replay.owner_source_id is None
    assert replay.preferred_source_id == "source-b"
    assert replay.project(payload, source_id="source-b", model=scope().model) == payload


def test_tampered_completed_state_is_not_discarded():
    opaque = codec()
    payload = history(opaque)
    payload["input"][0]["encrypted_content"] = "claude-v1.invalid"
    with pytest.raises(ClientPayloadError):
        read(payload, opaque, model="other")


def test_conflicting_active_search_owners_fail():
    opaque = codec()
    payload = search_history(opaque, completed=False)
    other = opaque.encode(OpaqueScope("source-b", scope().model, "key-a"), {"type": "web_search", "item_id": "x"})
    payload["input"].append({"type": "reasoning", "encrypted_content": other})
    with pytest.raises(ClientPayloadError, match="conflicting account owners") as rejected:
        read(payload, opaque)
    assert rejected.value.code == "invalid_provider_history"


def test_active_thinking_does_not_bind_its_account():
    opaque = codec()
    payload = history(opaque, completed=False)
    other = opaque.encode(OpaqueScope("source-b", "other", "key-a"), {"type": "thinking", "signature": "s"})
    payload["input"].append({"type": "reasoning", "encrypted_content": other})
    replay = read(payload, opaque)
    assert replay.owner_source_id is None
    assert replay.preferred_source_id == "source-b"
    assert replay.project(payload, source_id="source-c", model=scope().model) == payload


@pytest.mark.parametrize("completed", [True, False], ids=["new_user_turn", "closed_assistant_turn"])
def test_compaction_prefers_signed_owner_and_reads_thinking_elsewhere(caplog, completed):
    opaque = codec()
    payload = compact(history(opaque, completed=completed))
    original = deepcopy(payload)
    replay = read(payload, opaque, require_complete_history=True)
    assert replay.owner_source_id is None
    assert replay.preferred_source_id == "source-a"
    assert replay.project(payload, source_id="source-a", model=scope().model) == payload
    with caplog.at_level("INFO"):
        moved = replay.project(payload, source_id="source-b", model=scope().model)
    assert moved["input"] == [READABLE, *payload["input"][1:]]
    assert "converted=1 omitted=0" in caplog.text
    assert "private" not in caplog.text
    switched = read(payload, opaque, model="other", require_complete_history=True)
    assert switched.project(payload, source_id="source-a", model="other")["input"] == moved["input"]
    assert payload == original


@pytest.mark.parametrize("block", [{"type": "redacted_thinking", "data": "x"}, {"type": "thinking", "thinking": ""}])
def test_compaction_omits_unreadable_completed_state(block):
    opaque = codec()
    payload = compact(history(opaque))
    payload["input"][0]["encrypted_content"] = opaque.encode(scope(), block)
    replay = read(payload, opaque, model="other", require_complete_history=True)
    assert replay.project(payload, source_id="source-a", model="other")["input"] == payload["input"][1:]


def test_compaction_reads_conflicting_completed_owners():
    opaque = codec()
    payload = history(opaque)
    other = opaque.encode(OpaqueScope("source-b", scope().model, "key-a"), {"type": "thinking", "thinking": "second"})
    payload["input"].insert(1, {"type": "reasoning", "encrypted_content": other})
    payload = compact(payload)
    replay = read(payload, opaque, require_complete_history=True)
    assert replay.owner_source_id is None
    projected = replay.project(payload, source_id="source-b", model=scope().model)["input"]
    assert projected[:2] == [READABLE, payload["input"][1]]


def test_compaction_forwards_active_thinking_signed():
    opaque = codec()
    payload = history(opaque, completed=False)
    payload["input"][1] = {"type": "function_call", "name": "read", "call_id": "call", "arguments": "{}"}
    payload["input"].append({"type": "function_call_output", "call_id": "call", "output": "ok"})
    payload = compact(payload)
    replay = read(payload, opaque, require_complete_history=True)
    assert replay.owner_source_id is None
    assert replay.project(payload, source_id="source-b", model=scope().model) == payload
    switched = read(payload, opaque, model="other", require_complete_history=True)
    assert switched.project(payload, source_id="source-a", model="other") == payload


@pytest.mark.parametrize("pairing", [{}, {"call_id": None}, {"call_id": ""}, {"call_id": " \t"}])
def test_external_task_completes_prior_thinking_for_compaction(pairing):
    opaque = codec()
    payload = history(opaque, completed=False)
    payload["input"].append({**TASK_INPUT, **pairing})
    payload = compact(payload)
    original = deepcopy(payload)
    replay = read(payload, opaque, model="other", require_complete_history=True)
    assert replay.owner_source_id is None
    assert replay.project(payload, source_id="source-b", model="other")["input"] == [READABLE, *payload["input"][1:]]
    assert payload == original


@pytest.mark.parametrize("overrides", [{"call_id": "real"}, {"call_id": 1}, {"namespace": None}, {"output": ""}])
def test_unrecognized_task_does_not_complete_thinking(overrides):
    opaque = codec()
    payload = history(opaque, completed=False)
    payload["input"].append({**TASK_INPUT, **overrides})
    payload = compact(payload)
    replay = read(payload, opaque, model="other", require_complete_history=True)
    assert replay.project(payload, source_id="source-b", model="other") == payload


def test_external_task_completes_search_without_moving_its_state():
    opaque = codec()
    payload = search_history(opaque, completed=False)
    payload["input"].append(TASK_INPUT)
    replay = read(payload, opaque)
    assert replay.owner_source_id is None
    moved = replay.project(payload, source_id="source-b", model=scope().model)["input"]
    assert moved == [SEARCH_TEXT, *payload["input"][2:]]
    assert "upstream-owned-opaque-data" not in str(moved)


def test_tool_output_does_not_complete_search():
    opaque = codec()
    payload = search_history(opaque, completed=False)
    payload["input"].append({"type": "function_call_output", "call_id": "call", "output": "ok"})
    assert read(payload, opaque).owner_source_id == "source-a"
    with pytest.raises(ClientPayloadError):
        read(payload, opaque).project(payload, source_id="source-b", model=scope().model)


def test_external_task_does_not_skip_signed_history_authentication():
    opaque = codec()
    payload = history(opaque, completed=False)
    payload["input"].append(TASK_INPUT)
    with pytest.raises(ClientPayloadError):
        read(payload, opaque, client_scope="other", model="other")
