"""Semantic labels reuse validation and nested handoffs restore caller context."""

import asyncio
from types import SimpleNamespace

import pytest
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.clients.proxy import ProxyResponseError
from app.core.clock import REAL_SCHEDULER
from app.core.openai.exceptions import ClientPayloadError
from app.core.usage.request_operation import (
    RequestOperation,
    get_request_operation,
    refine_responses_operation,
    reset_request_operation,
    set_request_operation,
)
from app.core.utils.request_id import get_request_id, reset_request_id, set_request_id
from app.dependencies import ProxyContext
from app.modules.proxy import api
from app.modules.proxy.checkpoint_handoff import NativeCheckpointOrigin
from app.modules.proxy.replay_store import ApiKeyScope
from app.modules.proxy.request_policy import validate_top_level_compaction_trigger_input_shape

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("operation", list(RequestOperation))
@pytest.mark.parametrize("compacting", [False, True])
def test_refinement_only_changes_responses(operation, compacting):
    expected = RequestOperation.COMPACTION if operation == RequestOperation.RESPONSES and compacting else operation
    assert refine_responses_operation(operation, terminal_compaction=compacting) == expected


@pytest.mark.parametrize(
    "items,expected",
    [
        ("compaction_trigger", False),
        ([{"type": "context_compaction"}], False),
        ([{"role": "user", "content": "compaction_trigger"}], False),
        ([{"type": "compaction_trigger"}], True),
    ],
)
def test_validator_returns_existing_semantic_decision(items, expected):
    assert validate_top_level_compaction_trigger_input_shape({"input": items}) is expected


def test_validator_rejects_nonterminal_marker_before_refinement():
    with pytest.raises(ClientPayloadError):
        validate_top_level_compaction_trigger_input_shape({"input": [{"type": "compaction_trigger"}, "later"]})


@pytest.mark.parametrize("outcome", ["success", "error", "timeout", "cancel"])
@pytest.mark.parametrize(
    "parent",
    [
        RequestOperation.RESPONSES,
        RequestOperation.COMPACTION,
        RequestOperation.IMAGE_EDIT,
        RequestOperation.CHECKPOINT_HANDOFF,
    ],
)
async def test_auxiliary_handoff_restores_parent_on_every_exit(monkeypatch, outcome, parent):
    origin = NativeCheckpointOrigin("gpt-6.1-sol", "owner", {})
    seen = []
    active = asyncio.Event()

    class Handoff:
        def __init__(self, api_key, generate):
            self.generate = generate

        async def resolve(self, scope, checkpoint):
            return await self.generate(origin, checkpoint)

    async def collect(*args, **kwargs):
        seen.append((get_request_operation(), get_request_id()))
        active.set()
        await asyncio.sleep(0)
        if outcome == "error":
            raise RuntimeError("handoff failed")
        if outcome == "timeout":
            raise TimeoutError()
        if outcome == "cancel":
            raise asyncio.CancelledError()
        return JSONResponse({"status": "completed", "output": []})

    monkeypatch.setattr(api, "CheckpointHandoff", Handoff)
    monkeypatch.setattr(api, "_collect_responses", collect)
    context = ProxyContext(service=SimpleNamespace(scheduler=REAL_SCHEDULER))
    resolver = api._source_checkpoint_resolver(
        Request({"type": "http", "headers": [], "path": "/v1/responses"}),
        None,
        context,
    )
    token = set_request_operation(parent)
    id_token = set_request_id("parent-request")

    async def concurrent_parent():
        await active.wait()
        return get_request_operation(), get_request_id()

    concurrent = asyncio.create_task(concurrent_parent())
    try:
        if outcome == "success":
            await resolver(ApiKeyScope("key"), {"type": "compaction", "encrypted_content": "checkpoint"})
        else:
            expected_error = {"error": RuntimeError, "timeout": ProxyResponseError, "cancel": asyncio.CancelledError}[
                outcome
            ]
            with pytest.raises(expected_error):
                await resolver(ApiKeyScope("key"), {"type": "compaction", "encrypted_content": "checkpoint"})
        assert get_request_operation() == parent
        assert get_request_id() == "parent-request"
        assert await concurrent == (parent, "parent-request")
    finally:
        concurrent.cancel()
        await asyncio.gather(concurrent, return_exceptions=True)
        reset_request_operation(token)
        reset_request_id(id_token)
    assert seen[0][0] == RequestOperation.CHECKPOINT_HANDOFF
    assert seen[0][1].startswith("handoff_")
