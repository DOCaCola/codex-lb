"""Operation attribution at validated HTTP/source and websocket boundaries."""

import json

import pytest
from aiohttp import web
from sqlalchemy import select

from app.core.openai.compaction import encode_codex_lb_compaction_summary
from app.core.openai.models import CompactResponsePayload
from app.core.openai.requests import ResponsesCompactRequest
from app.core.usage.request_operation import (
    RequestOperation,
    get_request_operation,
    reset_request_operation,
    set_request_operation,
)
from app.db.models import RequestLog
from app.db.session import SessionLocal
from app.dependencies import get_proxy_service_for_app
from app.modules.proxy import service as proxy_service
from tests.integration import test_claude_provider_history as provider_fixtures
from tests.integration.model_source_helpers import _create_model_source, stub_source_upstreams
from tests.integration.test_claude_inference import install_upstream
from tests.integration.test_compaction_marker_routing import PATHS, websocket
from tests.integration.test_proxy_affinity_observation import _import_synthetic_account
from tests.integration.test_proxy_affinity_websocket_observation import SyntheticUpstream

pytestmark = pytest.mark.integration
opus_pool = provider_fixtures.opus_pool
TRIGGER = {"type": "compaction_trigger"}


async def operations(client):
    assert await client._transport.app.state.proxy_service.drain_persistence_tasks(timeout_seconds=5)
    async with SessionLocal() as session:
        rows = (await session.execute(select(RequestLog).order_by(RequestLog.id))).scalars().all()
        return [(row.request_operation, row.request_kind) for row in rows]


async def test_internal_compact_logs_actual_operation_without_ingress(async_client, monkeypatch):
    await _import_synthetic_account(async_client)

    async def compact(payload, *args, **kwargs):
        return CompactResponsePayload.model_validate(
            {
                "object": "response.compaction",
                "output": [{"type": "compaction", "encrypted_content": "native-checkpoint"}],
            }
        )

    monkeypatch.setattr(proxy_service, "core_compact_responses", compact)
    token = set_request_operation(RequestOperation.RESPONSES)
    try:
        await get_proxy_service_for_app(async_client._transport.app).compact_responses(
            ResponsesCompactRequest(model="gpt-6.1-sol", instructions="Keep context", input="Original task"),
            {},
        )
        assert get_request_operation() == RequestOperation.RESPONSES
    finally:
        reset_request_operation(token)
    assert await operations(async_client) == [("compaction", "normal")]


@pytest.mark.parametrize("path", PATHS)
@pytest.mark.parametrize("streaming", [False, True])
async def test_native_http_terminal_trigger_refines_operation(async_client, monkeypatch, path, streaming):
    await _import_synthetic_account(async_client)

    async def stream(payload, *args, **kwargs):
        yield 'data: {"type":"response.completed","response":{"id":"resp_native","status":"completed","output":[]}}\n\n'

    async def compact(payload, *args, **kwargs):
        return CompactResponsePayload.model_validate(
            {
                "object": "response.compaction",
                "output": [{"type": "compaction", "encrypted_content": "native-checkpoint"}],
            }
        )

    monkeypatch.setattr(proxy_service, "core_stream_responses", stream)
    monkeypatch.setattr(proxy_service, "core_compact_responses", compact)
    response = await async_client.post(
        path,
        json={"model": "gpt-6.1-sol", "instructions": "Retain context", "input": [TRIGGER], "stream": streaming},
    )
    assert response.status_code == 200, response.text
    logged = await operations(async_client)
    assert len(logged) == 1 and logged[0][0] == "compaction"


@pytest.mark.parametrize("path", PATHS)
async def test_native_websocket_operations_are_per_turn(async_client, monkeypatch, path):
    await _import_synthetic_account(async_client)

    async def connect(*args, **kwargs):
        return SyntheticUpstream()

    monkeypatch.setattr(proxy_service, "connect_responses_websocket", connect)
    async with websocket(async_client._transport.app, path) as turn:
        for items in ["Normal", [TRIGGER], "Normal again"]:
            result = await turn({"model": "gpt-6.1-sol", "instructions": "Keep context", "input": items})
            assert result["type"] == "response.completed", result
    assert await operations(async_client) == [
        ("responses", "normal"),
        ("compaction", "normal"),
        ("responses", "normal"),
    ]
    assert get_request_operation() == RequestOperation.UNKNOWN


@pytest.mark.parametrize("path", PATHS)
async def test_native_websocket_invalid_trigger_does_not_refine_next_turn(async_client, monkeypatch, path):
    await _import_synthetic_account(async_client)

    async def connect(*args, **kwargs):
        return SyntheticUpstream()

    monkeypatch.setattr(proxy_service, "connect_responses_websocket", connect)
    async with websocket(async_client._transport.app, path) as turn:
        rejected = await turn({"model": "gpt-6.1-sol", "input": [TRIGGER, {"role": "developer", "content": "Later"}]})
        assert rejected["type"] == "error" and rejected["error"]["code"] == "invalid_request_error", rejected
        normal = await turn({"model": "gpt-6.1-sol", "input": "Normal turn"})
        assert normal["type"] == "response.completed", normal
    assert [op for op, _ in await operations(async_client)] == ["responses"]


@pytest.mark.parametrize("path", PATHS)
@pytest.mark.parametrize("streaming", [False, True])
async def test_claude_synthetic_compaction_keeps_operation(async_client, opus_pool, monkeypatch, path, streaming):
    captured, _ = install_upstream(monkeypatch)
    result = await async_client.post(
        path,
        json={
            "model": provider_fixtures.MODEL,
            "instructions": "Keep context",
            "input": [{"role": "user", "content": "Original task"}, TRIGGER],
            "stream": streaming,
        },
    )
    assert result.status_code == 200, result.text
    assert "compaction_trigger" not in json.dumps(captured[-1][2])
    logged = await operations(async_client)
    assert len(logged) == 1 and logged[0][0] == "compaction"


@pytest.mark.parametrize("path", PATHS)
async def test_claude_websocket_compaction_does_not_leak(async_client, opus_pool, monkeypatch, path):
    install_upstream(monkeypatch)
    async with websocket(async_client._transport.app, path) as turn:
        for items in ["Normal", [{"role": "user", "content": "Task"}, TRIGGER], "Normal again"]:
            result = await turn({"model": provider_fixtures.MODEL, "instructions": "Keep context", "input": items})
            assert result["type"] == "response.completed", result
    logged = await operations(async_client)
    assert [op for op, _ in logged] == ["responses", "compaction", "responses"]
    assert get_request_operation() == RequestOperation.UNKNOWN


@pytest.mark.parametrize("path", PATHS)
async def test_compatible_source_compaction_snapshots_before_conversion(async_client, path):
    async def handler(request):
        body = await request.json()
        assert "compaction_trigger" not in json.dumps(body)
        return web.json_response(
            {
                "id": "resp_summary",
                "object": "response",
                "status": "completed",
                "output": [
                    {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "Summary"}]}
                ],
            }
        )

    async with stub_source_upstreams() as start:
        await _create_model_source(
            async_client,
            name="compact-source",
            model="compact-model",
            base_url=await start(handler),
            supports_responses=True,
        )
        result = await async_client.post(
            path,
            json={"model": "compact-model", "instructions": "Keep context", "input": ["Task", TRIGGER]},
        )
    assert result.status_code == 200, result.text
    assert [op for op, _ in await operations(async_client)] == ["compaction"]


@pytest.mark.parametrize("path", PATHS)
async def test_historical_checkpoints_and_client_claims_are_not_compaction(async_client, opus_pool, monkeypatch, path):
    install_upstream(monkeypatch)
    response = await async_client.post(
        path,
        headers={"x-codex-bridge-request-operation": "compaction"},
        json={
            "model": provider_fixtures.MODEL,
            "instructions": "compaction_trigger",
            "input": [
                {"type": "compaction", "encrypted_content": encode_codex_lb_compaction_summary("Retained history")},
                {"role": "user", "content": "compaction_trigger"},
            ],
            "client_metadata": {"request_operation": "compaction"},
        },
    )
    assert response.status_code == 200, response.text
    assert [op for op, _ in await operations(async_client)] == ["responses"]


@pytest.mark.parametrize("path", PATHS)
@pytest.mark.parametrize("items", [[TRIGGER, TRIGGER], [TRIGGER, {"role": "developer", "content": "Later"}]])
async def test_invalid_trigger_rejected_before_semantic_dispatch(async_client, opus_pool, monkeypatch, path, items):
    captured, _ = install_upstream(monkeypatch)
    response = await async_client.post(
        path,
        json={"model": provider_fixtures.MODEL, "instructions": "Keep context", "input": items},
    )
    assert response.status_code == 400, response.text
    assert not captured
    assert all(op != "compaction" for op, _ in await operations(async_client))
