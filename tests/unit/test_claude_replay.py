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


@pytest.mark.parametrize("kind", ["thinking", "redacted_thinking"])
def test_completed_history_is_soft_and_projection_is_immutable(kind):
    opaque = codec()
    payload = history(opaque, kind=kind)
    original = deepcopy(payload)
    replay = read(payload, opaque)
    assert replay.owner_source_id is None
    assert replay.preferred_source_id == "source-a"
    assert replay.project(payload, source_id="source-a", model=scope().model) == payload
    assert replay.project(payload, source_id="source-b", model=scope().model)["input"] == payload["input"][1:]
    assert (
        read(payload, opaque, model="other").project(payload, source_id="source-a", model="other")["input"]
        == payload["input"][1:]
    )
    assert payload == original


@pytest.mark.parametrize("kind,completed", [("thinking", False), ("web_search", True)])
def test_strict_history_cannot_move(kind, completed):
    opaque = codec()
    payload = history(opaque, kind=kind, completed=completed)
    replay = read(payload, opaque)
    assert replay.owner_source_id == "source-a"
    with pytest.raises(ClientPayloadError):
        replay.project(payload, source_id="source-b", model=scope().model)
    with pytest.raises(ClientPayloadError):
        read(payload, opaque, model="other")


def test_tool_output_does_not_complete_thinking():
    opaque = codec()
    payload = history(opaque, completed=False)
    payload["input"].append({"type": "function_call_output", "call_id": "call", "output": "ok"})
    assert read(payload, opaque).owner_source_id == "source-a"


def test_authentication_precedes_omission():
    opaque = codec()
    with pytest.raises(ClientPayloadError):
        read(history(opaque), opaque, client_scope="other")


def test_mixed_completed_owners_are_not_conflicting():
    opaque = codec()
    payload = history(opaque)
    other = opaque.encode(OpaqueScope("source-b", scope().model, "key-a"), {"type": "thinking"})
    payload["input"].insert(1, {"type": "reasoning", "encrypted_content": other})
    replay = read(payload, opaque)
    assert replay.owner_source_id is None
    assert replay.preferred_source_id == "source-b"
    assert len(replay.project(payload, source_id="source-b", model=scope().model)["input"]) == 3


def test_tampered_completed_state_is_not_discarded():
    opaque = codec()
    payload = history(opaque)
    payload["input"][0]["encrypted_content"] = "claude-v1.invalid"
    with pytest.raises(ClientPayloadError):
        read(payload, opaque, model="other")


def test_conflicting_active_owners_fail():
    opaque = codec()
    payload = history(opaque, completed=False)
    other = opaque.encode(OpaqueScope("source-b", scope().model, "key-a"), {"type": "thinking"})
    payload["input"].append({"type": "reasoning", "encrypted_content": other})
    with pytest.raises(ClientPayloadError):
        read(payload, opaque)


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


@pytest.mark.parametrize("kind", ["thinking", "web_search"])
def test_compaction_keeps_active_and_search_state_strict(kind):
    opaque = codec()
    payload = history(opaque, kind=kind, completed=kind == "web_search")
    if kind == "thinking":
        payload["input"][1] = {"type": "function_call", "name": "read", "call_id": "call", "arguments": "{}"}
        payload["input"].append({"type": "function_call_output", "call_id": "call", "output": "ok"})
    payload = compact(payload)
    replay = read(payload, opaque, require_complete_history=True)
    assert replay.owner_source_id == "source-a"
    with pytest.raises(ClientPayloadError, match="original account/model"):
        replay.project(payload, source_id="source-b", model=scope().model)
    with pytest.raises(ClientPayloadError, match="original model"):
        read(payload, opaque, model="other", require_complete_history=True)


@pytest.mark.parametrize("pairing", [{}, {"call_id": None}, {"call_id": ""}, {"call_id": " \t"}])
def test_external_task_completes_prior_thinking_without_mutating_replay(pairing):
    opaque = codec()
    payload = history(opaque, completed=False)
    payload["input"].append({**TASK_INPUT, **pairing})
    original = deepcopy(payload)
    replay = read(payload, opaque, model="other")
    assert replay.owner_source_id is None
    assert replay.project(payload, source_id="source-b", model="other")["input"] == payload["input"][1:]
    assert payload == original


@pytest.mark.parametrize("overrides", [{"call_id": "real"}, {"call_id": 1}, {"namespace": None}, {"output": ""}])
def test_unrecognized_task_does_not_complete_thinking(overrides):
    opaque = codec()
    payload = history(opaque, completed=False)
    payload["input"].append({**TASK_INPUT, **overrides})
    assert read(payload, opaque).owner_source_id == "source-a"
    with pytest.raises(ClientPayloadError):
        read(payload, opaque, model="other")


def test_external_task_does_not_relax_search_ownership():
    opaque = codec()
    payload = history(opaque, kind="web_search", completed=False)
    payload["input"].append(TASK_INPUT)
    replay = read(payload, opaque)
    assert replay.owner_source_id == "source-a"
    with pytest.raises(ClientPayloadError):
        replay.project(payload, source_id="source-b", model=scope().model)


def test_external_task_does_not_skip_signed_history_authentication():
    opaque = codec()
    payload = history(opaque, completed=False)
    payload["input"].append(TASK_INPUT)
    with pytest.raises(ClientPayloadError):
        read(payload, opaque, client_scope="other", model="other")
