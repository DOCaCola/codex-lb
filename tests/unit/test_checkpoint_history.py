import json
import os
from copy import deepcopy

import pytest

from app.core.openai.compaction import lower_opaque_compaction_items_for_model_source
from app.core.openai.exceptions import ClientPayloadError
from app.core.openai.models import CompactResponsePayload
from app.core.openai.requests import ResponsesCompactRequest
from app.modules.proxy.checkpoint_history import (
    CheckpointHistory,
    UnreadableCheckpointHistory,
    readable_checkpoint_input,
)
from app.modules.proxy.replay_store import HTTPFallbackReplayStore, ReplayScope

pytestmark = pytest.mark.unit


def message(text, role="user"):
    return {"type": "message", "role": role, "content": text}


def checkpoint(token="PRIVATE_CIPHERTEXT"):
    return {"type": "compaction", "id": "cmp_test", "encrypted_content": token}


def request(items, **kwargs):
    return ResponsesCompactRequest(model="gpt-6.1-sol", instructions="Keep constraints", input=items, **kwargs)


def response(token="PRIVATE_CIPHERTEXT", prefix=None, **kwargs):
    return CompactResponsePayload.model_validate(
        {"object": "response.compaction", "output": [*(prefix or []), checkpoint(token)], **kwargs}
    )


def history():
    return [
        message("Original task"),
        {"type": "additional_tools", "tools": [{"type": "function", "name": "PRIVATE_ADVERTISEMENT"}]},
        {"type": "context_compaction", "encrypted_content": None},
        {
            "type": "reasoning",
            "id": "rs_secret",
            "encrypted_content": "PRIVATE_REASONING_CIPHERTEXT",
            "summary": [{"type": "summary_text", "text": "Useful reasoning"}],
            "content": [{"type": "reasoning_text", "text": "Useful reasoning"}],
        },
        {"type": "reasoning", "encrypted_content": "PRIVATE_ONLY_CIPHERTEXT"},
        {"type": "function_call", "id": "fc_transport", "name": "read", "call_id": "call_1", "arguments": "{}"},
        {"type": "function_call_output", "call_id": "call_1", "output": "Critical evidence" + "x" * 10_000},
        {
            **message("Done", "assistant"),
            "id": "msg_transport",
            "status": "completed",
            "internal_chat_message_metadata_passthrough": {"PRIVATE_TELEMETRY": "secret"},
        },
        {
            "type": "message",
            "role": "user",
            "content": [{"type": "input_image", "image_url": "data:image/png;base64,AA=="}],
        },
        message("Repeat"),
        message("Repeat"),
    ]


def test_projection_preserves_semantics_without_protocol_debris():
    original = history()
    snapshot = deepcopy(original)
    projected = readable_checkpoint_input(original)
    wire = json.dumps(projected)
    assert "PRIVATE" not in wire and "encrypted_content" not in wire
    assert "fc_transport" not in wire and "msg_transport" not in wire
    assert wire.count("Useful reasoning") == 1
    assert "Critical evidence" + "x" * 10_000 in wire
    assert "data:image/png;base64,AA==" in wire
    assert projected[-2:] == [message("Repeat"), message("Repeat")]
    assert snapshot == original


@pytest.mark.parametrize(
    "item",
    [
        {"type": "mcp_call", "output": "meaningful"},
        {"type": "item_reference", "id": "external"},
        {"type": "compaction", "encrypted_content": "unknown"},
        {"type": "function_call_output", "call_id": "missing", "output": "needed"},
        {"type": "message", "role": "user", "content": [{"type": "input_file", "file_id": "file_bound"}]},
        {"type": "context_compaction", "content": "not metadata"},
        {"type": ["message"]},
        {"type": "reasoning", "summary": "not an array"},
    ],
)
def test_unknown_or_bound_state_is_not_partially_projected(item):
    with pytest.raises(UnreadableCheckpointHistory):
        readable_checkpoint_input([message("Keep this"), item])


@pytest.mark.asyncio
async def test_successful_checkpoint_scope_restart_and_content_free_storage(tmp_path, caplog):
    scope = ReplayScope("key", "thread")
    store = HTTPFallbackReplayStore(tmp_path)
    service = CheckpointHistory(store, scope)
    req = request(history())
    res = response()
    before = req.model_dump()
    await service.remember(req, res, "owner")
    raw = b"".join(path.read_bytes() for path in tmp_path.glob("*.replay"))
    assert b"PRIVATE" not in raw and b"encrypted_content" not in raw
    payload = {"input": [checkpoint(), message("Continue")]}
    restarted = CheckpointHistory(HTTPFallbackReplayStore(tmp_path), scope)
    recovered = await restarted.materialize(payload)
    assert recovered["input"] == [
        message("Keep constraints", "developer"),
        *readable_checkpoint_input(req.input),
        message("Continue"),
    ]
    assert req.model_dump() == before and payload["input"][0] == checkpoint()
    for other_scope in [None, ReplayScope("other", "thread"), ReplayScope("key", "other")]:
        if other_scope is None:
            assert await CheckpointHistory(store, other_scope).materialize(payload) == payload
        else:
            with pytest.raises(ClientPayloadError):
                await CheckpointHistory(store, other_scope).materialize(payload)
    assert "PRIVATE" not in caplog.text


@pytest.mark.asyncio
async def test_compact_replacement_prefix_is_removed_exactly_once(tmp_path):
    service = CheckpointHistory(HTTPFallbackReplayStore(tmp_path), ReplayScope("key", "thread"))
    original = [message("Task"), message("Keep"), message("Older answer", "assistant")]
    prefix = [message("Keep")]
    await service.remember(request(original), response(prefix=prefix), "owner")
    recovered = await service.materialize({"input": [message("Keep"), *prefix, checkpoint(), message("Next")]})
    assert recovered["input"] == [
        message("Keep"),
        message("Keep constraints", "developer"),
        *readable_checkpoint_input(request(original).input),
        message("Next"),
    ]
    different = await service.materialize({"input": [message("Different"), checkpoint()]})
    assert different["input"][0] == message("Different")


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["failed", "incomplete", "in_progress"])
async def test_noncompleted_compaction_does_not_seed_recovery(tmp_path, status):
    service = CheckpointHistory(HTTPFallbackReplayStore(tmp_path), ReplayScope("key", "thread"))
    await service.remember(request(history()), response(status=status), "owner")
    assert not list(tmp_path.glob("*.replay"))


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "kwargs",
    [{"previous_response_id": "resp_missing"}, {"conversation": "conv_bound"}, {"prompt": {"id": "prompt_bound"}}],
)
async def test_unresolved_native_handle_does_not_seed_recovery(tmp_path, kwargs):
    service = CheckpointHistory(HTTPFallbackReplayStore(tmp_path), ReplayScope("key", "thread"))
    await service.remember(request(history(), **kwargs), response(), "owner")
    assert not list(tmp_path.glob("*.replay"))


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["expired", "corrupt", "evicted", "oversize"])
async def test_unavailable_state_keeps_explicit_checkpoint_error(tmp_path, failure):
    scope = ReplayScope("key", "thread")
    store = HTTPFallbackReplayStore(tmp_path, max_entries=1, max_entry_bytes=100 if failure == "oversize" else 100_000)
    service = CheckpointHistory(store, scope)
    await service.remember(request(history()), response(), "owner")
    if failure == "expired":
        path = next(tmp_path.glob("*.replay"))
        stamp = path.stat().st_mtime - 3601
        os.utime(path, (stamp, stamp))
    elif failure == "corrupt":
        path = next(tmp_path.glob("*.replay"))
        path.write_bytes(b"bad digest\n{}")
    elif failure == "evicted":
        await service.remember(request([message("New task")]), response("new"), "owner")
    with pytest.raises(ClientPayloadError, match="cannot read the compaction checkpoint"):
        recovered = await service.materialize({"input": [checkpoint()]})
        lower_opaque_compaction_items_for_model_source(recovered)


@pytest.mark.asyncio
async def test_chained_compact_materializes_before_previous_record_eviction(tmp_path):
    store = HTTPFallbackReplayStore(tmp_path, max_entries=1)
    service = CheckpointHistory(store, ReplayScope("key", "thread"))
    await service.remember(request([message("Original context")]), response("first"), "owner")
    await service.remember(request([checkpoint("first"), message("New evidence")]), response("second"), "owner")
    recovered = await service.materialize({"input": [checkpoint("second"), message("Continue")]})
    assert recovered["input"] == [
        message("Keep constraints", "developer"),
        message("Original context"),
        message("New evidence"),
        message("Continue"),
    ]
    with pytest.raises(ClientPayloadError):
        await service.materialize({"input": [checkpoint("first")]})


@pytest.mark.asyncio
async def test_mixed_checkpoints_fail_at_original_index_without_partial_mutation(tmp_path):
    service = CheckpointHistory(HTTPFallbackReplayStore(tmp_path), ReplayScope("key", "thread"))
    await service.remember(request(history()), response(), "owner")
    payload = {"input": [checkpoint(), checkpoint("unobserved")]}
    original = deepcopy(payload)
    with pytest.raises(ClientPayloadError) as caught:
        await service.materialize(payload)
    assert caught.value.param == "input[1]"
    assert payload == original


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "items",
    [[], [{"type": "reasoning", "encrypted_content": "private"}], [{"type": "mcp_call", "output": "important"}]],
)
async def test_empty_or_unrecoverable_semantic_history_is_not_retained(tmp_path, items):
    service = CheckpointHistory(HTTPFallbackReplayStore(tmp_path), ReplayScope("key", "thread"))
    await service.remember(request(items), response(), "owner")
    assert not list(tmp_path.glob("*.replay"))
