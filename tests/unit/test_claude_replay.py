from copy import deepcopy

import pytest

from app.core.openai.exceptions import ClientPayloadError
from app.modules.claude.opaque import OpaqueScope
from app.modules.claude.replay import authenticate_replay
from tests.unit.test_claude_protocol import TASK_INPUT, codec, scope

pytestmark = pytest.mark.unit


def history(opaque, *, kind="thinking", completed=True):
    token = opaque.encode(scope(), {"type": kind, "thinking": "private", "signature": "signed"})
    items = [{"type": "reasoning", "encrypted_content": token}, {"role": "assistant", "content": "answer"}]
    if completed:
        items.append({"role": "user", "content": "next"})
    return {"input": items}


def read(payload, opaque, **overrides):
    return authenticate_replay(
        payload,
        opaque,
        **{"model": scope().model, "client_scope": "key-a", "conversation_id": "thread-a", **overrides},
    )


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


@pytest.mark.parametrize("field,value", [("client_scope", "other"), ("conversation_id", "other")])
def test_authentication_precedes_omission(field, value):
    opaque = codec()
    with pytest.raises(ClientPayloadError):
        read(history(opaque), opaque, **{field: value})


def test_mixed_completed_owners_are_not_conflicting():
    opaque = codec()
    payload = history(opaque)
    other = opaque.encode(OpaqueScope("source-b", scope().model, "key-a", "thread-a"), {"type": "thinking"})
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
    other = opaque.encode(OpaqueScope("source-b", scope().model, "key-a", "thread-a"), {"type": "thinking"})
    payload["input"].append({"type": "reasoning", "encrypted_content": other})
    with pytest.raises(ClientPayloadError):
        read(payload, opaque)


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
