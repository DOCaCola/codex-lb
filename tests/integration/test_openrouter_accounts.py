from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock

import pytest
from aiohttp import web
from sqlalchemy import select
from starlette.requests import Request

from app.core.auth import dependencies as auth_dependencies
from app.core.auth.dashboard_access import guest_principal
from app.core.openai.compaction import decode_codex_lb_compaction_summary
from app.core.openai.exceptions import ClientPayloadError
from app.db.models import ModelSource, RequestLog
from app.db.session import SessionLocal
from app.dependencies import get_proxy_service_for_app
from app.modules.model_sources.continuation import SourceContinuation
from app.modules.openrouter import routing
from app.modules.openrouter.client import OpenRouterClient, OpenRouterError
from app.modules.openrouter.schemas import CatalogResponse, CreditInfo, KeyInfo
from tests.integration.model_source_helpers import _enable_api_key_auth, stub_source_upstreams

pytestmark = pytest.mark.integration


@pytest.fixture
def provider(monkeypatch):
    catalog = CatalogResponse.model_validate(
        {
            "data": [
                {
                    "id": "vendor/test",
                    "name": "Test model",
                    "context_length": 1_000_000,
                    "architecture": {"input_modalities": ["text", "image"], "output_modalities": ["text"]},
                    "pricing": {"prompt": "0.000001", "completion": "0.000002"},
                    "top_provider": {"context_length": 500_000, "max_completion_tokens": 32000},
                    "supported_parameters": ["tools", "reasoning"],
                    "reasoning": {"mandatory": True, "supported_efforts": None, "default_effort": "high"},
                }
            ]
        }
    )

    async def key_info(self, key):
        if key == "invalid":
            raise OpenRouterError("OpenRouter /key returned HTTP 401")
        return KeyInfo(usage=1, usage_daily=1, usage_weekly=1, usage_monthly=1, is_free_tier=False)

    async def models(self, key):
        return catalog

    monkeypatch.setattr(OpenRouterClient, "key_info", key_info)
    monkeypatch.setattr(OpenRouterClient, "catalog", models)
    return catalog


@pytest.mark.parametrize("path", ["/v1/responses", "/backend-api/codex/responses"])
@pytest.mark.parametrize("parallel", [True, False])
async def test_websocket_parameter_rejection_is_terminal(async_client, provider, path, parallel):
    calls = []

    async def upstream(request):
        body = await request.json()
        calls.append(body)
        assert "parallel_tool_calls" not in body
        assert body["provider"] == {"sort": "price", "require_parameters": True}
        return web.json_response({"error": {"code": 404, "message": "No endpoints found"}}, status=404)

    async with stub_source_upstreams() as start:
        url = await start(upstream)
        created = await async_client.post("/api/openrouter-accounts", json={"name": "WS", "apiKey": "secret-test"})
        account_id = created.json()["id"]
        await async_client.patch(
            f"/api/openrouter-accounts/{account_id}", json={"selections": [{"model": "vendor/test"}]}
        )
        async with SessionLocal() as session:
            source = await session.get(ModelSource, account_id)
            source.base_url = url
            await session.commit()
        incoming, outgoing = asyncio.Queue(), asyncio.Queue()
        scope = {
            "type": "websocket",
            "asgi": {"version": "3.0"},
            "scheme": "ws",
            "path": path,
            "raw_path": path.encode(),
            "query_string": b"",
            "root_path": "",
            "headers": [(b"user-agent", b"codex_cli_rs/0.157.0")],
            "client": ("127.0.0.1", 12345),
            "server": ("testserver", 80),
            "subprotocols": [],
        }
        task = asyncio.create_task(async_client._transport.app(scope, incoming.get, outgoing.put))
        try:
            await incoming.put({"type": "websocket.connect"})
            assert (await asyncio.wait_for(outgoing.get(), 5))["type"] == "websocket.accept"
            # Two rejected turns prove the bridge finishes each turn without wedging the connection.
            for _ in range(2):
                await incoming.put(
                    {
                        "type": "websocket.receive",
                        "text": json.dumps(
                            {
                                "type": "response.create",
                                "model": "openrouter/vendor/test",
                                "input": "Hello",
                                "parallel_tool_calls": parallel,
                            }
                        ),
                    }
                )
                message = await asyncio.wait_for(outgoing.get(), 5)
                assert message["type"] == "websocket.send"
                event = json.loads(message["text"])
                assert event["type"] == "error"
                assert event["status"] == (404 if parallel else 400)
                # Mirrors Codex's WrappedWebsocketError string field contract.
                assert event["error"]["code"] == ("404" if parallel else "unsupported_parameter")
                assert isinstance(event["error"]["message"], str)
                assert event["error"]["type"] == "invalid_request_error"
                if parallel:
                    assert event["error"]["message"] == "No endpoints found"
            assert len(calls) == (2 if parallel else 0)
        finally:
            await incoming.put({"type": "websocket.disconnect", "code": 1000})
            try:
                await asyncio.wait_for(task, 5)
            finally:
                if not task.done():
                    task.cancel()
                await asyncio.gather(task, return_exceptions=True)


async def test_account_lifecycle_selection_and_disappearance(async_client, provider):
    created = await async_client.post("/api/openrouter-accounts", json={"name": "Native", "apiKey": "secret-test"})
    assert created.status_code == 200, created.text
    account = created.json()
    assert "secret-test" not in created.text
    assert account["state"]["selections"] == []
    assert account["state"]["credits"] is None
    account_id = account["id"]
    selected = await async_client.patch(
        f"/api/openrouter-accounts/{account_id}",
        json={
            "selections": [{"model": "vendor/test"}],
        },
    )
    assert selected.status_code == 200, selected.text
    assert selected.json()["state"]["selections"][0]["contextWindow"] == 262144
    provider.data = []
    refreshed = await async_client.post(f"/api/openrouter-accounts/{account_id}/refresh")
    assert refreshed.status_code == 200, refreshed.text
    assert refreshed.json()["state"]["selections"][0]["model"] == "vendor/test"
    denied = await async_client.post("/v1/responses", json={"model": "openrouter/vendor/test", "input": "Hi"})
    assert denied.status_code == 503, denied.text
    assert denied.json()["error"]["code"] == "model_source_disabled"
    deleted = await async_client.delete(f"/api/openrouter-accounts/{account_id}")
    assert deleted.status_code == 204
    assert (await async_client.get("/api/openrouter-accounts")).json() == {"accounts": []}


async def test_invalid_credentials_do_not_create_account(async_client, provider):
    result = await async_client.post("/api/openrouter-accounts", json={"name": "Invalid", "apiKey": "invalid"})
    assert result.status_code == 400
    assert (await async_client.get("/api/openrouter-accounts")).json() == {"accounts": []}


async def test_credit_monitoring_uses_separate_key_and_retains_stale_snapshot(async_client, provider, monkeypatch):
    async def credits(self, key):
        assert key == "management-secret"
        return CreditInfo(total_credits=100, total_usage=30)

    monkeypatch.setattr(OpenRouterClient, "credits", credits)
    created = await async_client.post(
        "/api/openrouter-accounts",
        json={
            "name": "Monitored",
            "apiKey": "inference-secret",
            "managementKey": "management-secret",
        },
    )
    assert created.status_code == 200, created.text
    assert "secret" not in created.text
    assert created.json()["state"]["credits"] == {"total_credits": 100, "total_usage": 30}
    account_id = created.json()["id"]

    async def failed(self, key):
        raise OpenRouterError("OpenRouter /credits could not be reached")

    monkeypatch.setattr(OpenRouterClient, "credits", failed)
    refreshed = await async_client.post(f"/api/openrouter-accounts/{account_id}/refresh")
    assert refreshed.json()["state"]["credits"] == created.json()["state"]["credits"]
    assert refreshed.json()["state"]["credits_error"]


async def test_failed_catalog_refresh_retains_selection(async_client, provider, monkeypatch):
    created = await async_client.post("/api/openrouter-accounts", json={"name": "Native", "apiKey": "secret-test"})
    account_id = created.json()["id"]
    await async_client.patch(f"/api/openrouter-accounts/{account_id}", json={"selections": [{"model": "vendor/test"}]})

    async def unavailable(self, key):
        raise OpenRouterError("OpenRouter /models/user could not be reached")

    monkeypatch.setattr(OpenRouterClient, "catalog", unavailable)
    result = await async_client.post(f"/api/openrouter-accounts/{account_id}/refresh")
    assert result.status_code == 200
    state = result.json()["state"]
    assert state["catalog_error"]
    assert state["catalog"][0]["id"] == "vendor/test"
    assert state["selections"][0]["model"] == "vendor/test"


@pytest.mark.parametrize("status", [401, 402, 429, 403, 503])
@pytest.mark.parametrize("scoped", [False, True])
async def test_explicit_rejection_fails_over_before_delivery(async_client, provider, status, scoped):
    calls = []

    async def limited(request):
        calls.append("limited")
        return web.json_response(
            {"error": {"message": "Rate limited", "type": "rate_limit_error"}},
            status=status,
            headers={"Retry-After": "120"},
        )

    async def success(request):
        calls.append("success")
        body = await request.json()
        assert body["model"] == "vendor/test"
        assert body["store"] is False
        assert body["provider"] == {"sort": "price", "require_parameters": True}
        return web.json_response(
            {
                "id": "resp_success",
                "object": "response",
                "status": "completed",
                "output": [],
                "usage": {"input_tokens": 10, "output_tokens": 2, "total_tokens": 12, "cost": 0.001},
            }
        )

    async with stub_source_upstreams() as start:
        source_ids = []
        for name, handler in (("A", limited), ("B", success)):
            created = await async_client.post("/api/openrouter-accounts", json={"name": name, "apiKey": "secret-test"})
            account_id = created.json()["id"]
            source_ids.append(account_id)
            await async_client.patch(
                f"/api/openrouter-accounts/{account_id}", json={"selections": [{"model": "vendor/test"}]}
            )
            url = await start(handler)
            async with SessionLocal() as session:
                source = await session.get(ModelSource, account_id)
                assert source is not None
                source.base_url = url
                await session.commit()
        routing._rotation.clear()
        headers = {}
        if scoped:
            await _enable_api_key_auth(async_client)
            key = await async_client.post(
                "/api/api-keys/", json={"name": "Scoped", "assignedSourceIds": [source_ids[0]]}
            )
            assert key.status_code == 200, key.text
            headers = {"Authorization": f"Bearer {key.json()['key']}"}
        result = await async_client.post(
            "/v1/responses",
            json={"model": "openrouter/vendor/test", "input": "Hi", "stream": False},
            headers=headers,
        )
        if scoped or status in (403, 503):
            assert result.status_code >= 400, result.text
            assert calls == ["limited"]
            return
        assert result.status_code == 200, result.text
        assert calls == ["limited", "success"]
        result = await async_client.post(
            "/v1/responses", json={"model": "openrouter/vendor/test", "input": "Again", "stream": False}
        )
        assert result.status_code == 200, result.text
        assert calls == ["limited", "success", "success"]
        async with SessionLocal() as session:
            costs = list(
                await session.scalars(select(RequestLog.cost_usd).where(RequestLog.model_source_id == source_ids[1]))
            )
            assert costs == [pytest.approx(0.001), pytest.approx(0.001)]


async def test_read_only_account_mutations_denied(async_client, provider, monkeypatch):
    app = async_client._transport.app
    original = auth_dependencies.validate_dashboard_session
    principal = guest_principal()
    monkeypatch.setattr(auth_dependencies, "validate_dashboard_session", AsyncMock(return_value=principal))
    monkeypatch.setitem(app.dependency_overrides, original, lambda: principal)
    result = await async_client.post("/api/openrouter-accounts", json={"name": "Denied", "apiKey": "secret-test"})
    assert result.status_code == 403
    assert result.json()["error"]["code"] == "read_only_access"


async def test_source_history_can_switch_to_native_without_pinning_source_account(async_client):
    headers = {"user-agent": "codex_cli_rs/0.154.0", "session_id": "switch-session"}
    request = Request({"type": "http", "headers": [(key.encode(), value.encode()) for key, value in headers.items()]})
    continuation = SourceContinuation(request, None, "src_old_provider")
    await continuation.expand({"model": "openrouter/vendor/test", "input": [{"role": "user", "content": "Original"}]})
    await continuation.remember(
        {
            "id": "resp_source_switch",
            "status": "completed",
            "output": [
                {
                    "type": "message",
                    "id": "msg_source",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": "Answer"}],
                },
            ],
        }
    )
    service = get_proxy_service_for_app(async_client._transport.app)
    prepared = await service._prepare_websocket_response_create_request(
        {
            "type": "response.create",
            "model": "gpt-5.4",
            "input": "Continue",
            "previous_response_id": "resp_source_switch",
        },
        headers=headers,
        codex_session_affinity=True,
        openai_cache_affinity=True,
        sticky_threads_enabled=False,
        openai_cache_affinity_max_age_seconds=300,
        api_key=None,
    )
    assert prepared.request_state.preferred_account_id != "src_old_provider"
    assert prepared.request_state.replay_required_account_id != "src_old_provider"
    assert prepared.request_state.request_text is not None
    payload = json.loads(prepared.request_state.request_text)
    assert not payload.get("previous_response_id")
    assert len(payload["input"]) == 3
    assert "Original" in json.dumps(payload["input"])


async def test_missing_source_history_never_dispatches_incomplete_input(async_client):
    request = Request({"type": "http", "headers": [(b"session_id", b"missing-session")]})
    continuation = SourceContinuation(request, None, "src_provider")
    with pytest.raises(ClientPayloadError, match="resend complete history"):
        await continuation.expand(
            {"model": "openrouter/vendor/test", "previous_response_id": "resp_expired", "input": "Continue"}
        )


@pytest.mark.parametrize("path", ["/v1/responses", "/backend-api/codex/responses"])
@pytest.mark.parametrize("custom", [False, True])
@pytest.mark.parametrize("reconnect", [False, True])
async def test_websocket_source_tool_continuation(async_client, provider, path, custom, reconnect):
    requests = []

    async def upstream(request):
        body = await request.json()
        requests.append(body)
        response_id = f"resp_tool_{len(requests)}"
        output = (
            [{"type": "function_call", "id": "fc_test", "call_id": "call_test", "name": "lookup", "arguments": "{}"}]
            if len(requests) == 1
            else []
        )
        if custom and output:
            output = [
                {
                    "type": "custom_tool_call",
                    "id": "ct_test",
                    "call_id": "call_test",
                    "name": "lookup",
                    "namespace": "functions",
                    "input": "lookup test",
                }
            ]
        event = {
            "type": "response.completed",
            "response": {
                "id": response_id,
                "object": "response",
                "status": "completed",
                "output": output,
                "usage": {"input_tokens": 10, "output_tokens": 2, "total_tokens": 12, "cost": 0.001},
            },
        }
        return web.Response(text=f"data: {json.dumps(event)}\n\n", content_type="text/event-stream")

    async with stub_source_upstreams() as start:
        url = await start(upstream)
        created = await async_client.post("/api/openrouter-accounts", json={"name": "WS", "apiKey": "secret-test"})
        account_id = created.json()["id"]
        await async_client.patch(
            f"/api/openrouter-accounts/{account_id}", json={"selections": [{"model": "vendor/test"}]}
        )
        async with SessionLocal() as session:
            source = await session.get(ModelSource, account_id)
            assert source is not None
            source.base_url = url
            await session.commit()

        incoming = asyncio.Queue()
        outgoing = asyncio.Queue()
        scope = {
            "type": "websocket",
            "asgi": {"version": "3.0"},
            "scheme": "ws",
            "path": path,
            "raw_path": path.encode(),
            "query_string": b"",
            "root_path": "",
            "headers": [(b"user-agent", b"codex_cli_rs/0.154.0"), (b"session_id", b"test-openrouter-session")],
            "client": ("127.0.0.1", 12345),
            "server": ("testserver", 80),
            "subprotocols": [],
        }
        app = async_client._transport.app
        task = asyncio.create_task(app(scope, incoming.get, outgoing.put))
        try:
            await incoming.put({"type": "websocket.connect"})
            accepted = await asyncio.wait_for(outgoing.get(), 5)
            assert accepted["type"] == "websocket.accept", accepted
            for turn in range(2):
                if turn and reconnect:
                    await incoming.put({"type": "websocket.disconnect", "code": 1000})
                    await asyncio.wait_for(task, 5)
                    incoming = asyncio.Queue()
                    outgoing = asyncio.Queue()
                    task = asyncio.create_task(app(dict(scope), incoming.get, outgoing.put))
                    await incoming.put({"type": "websocket.connect"})
                    accepted = await asyncio.wait_for(outgoing.get(), 5)
                    assert accepted["type"] == "websocket.accept", accepted
                payload = {"type": "response.create", "model": "openrouter/vendor/test", "input": "Hello"}
                if custom:
                    payload["tools"] = [
                        {
                            "type": "namespace",
                            "name": "functions",
                            "tools": [
                                {"type": "custom", "name": "lookup", "format": {"type": "text"}},
                            ],
                        }
                    ]
                if turn:
                    payload.update(
                        previous_response_id="resp_tool_1",
                        input=[
                            {
                                "type": "custom_tool_call_output" if custom else "function_call_output",
                                "call_id": "call_test",
                                "output": "result",
                            }
                        ],
                    )
                await incoming.put({"type": "websocket.receive", "text": json.dumps(payload)})
                while True:
                    message = await asyncio.wait_for(outgoing.get(), 10)
                    assert message["type"] == "websocket.send", message
                    event = json.loads(message["text"])
                    assert event["type"] not in ("error", "response.failed"), event
                    if event["type"] == "response.completed":
                        break
            assert len(requests) == 2
            assert not requests[1].get("previous_response_id")
            assert [item["type"] for item in requests[1]["input"] if "type" in item][-2:] == (
                ["custom_tool_call", "custom_tool_call_output"] if custom else ["function_call", "function_call_output"]
            )
            if custom:
                assert requests[1]["input"][-2]["namespace"] == "functions"
                assert requests[1]["tools"][0]["type"] == "namespace"
        finally:
            await incoming.put({"type": "websocket.disconnect", "code": 1000})
            try:
                await asyncio.wait_for(task, 5)
            finally:
                if not task.done():
                    task.cancel()
                await asyncio.gather(task, return_exceptions=True)


@pytest.mark.parametrize("path", ["/v1/responses/compact", "/backend-api/codex/responses/compact"])
async def test_source_compaction_uses_selected_provider(async_client, provider, path):
    async def upstream(request):
        payload = await request.json()
        assert payload["model"] == "vendor/test"
        assert payload["stream"] is False
        assert payload["store"] is False
        assert payload["input"][-1]["role"] == "user"
        return web.json_response(
            {
                "id": "resp_summary",
                "object": "response",
                "status": "completed",
                "output": [
                    {
                        "type": "message",
                        "status": "completed",
                        "content": [{"type": "output_text", "text": "Preserved summary"}],
                    }
                ],
                "usage": {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15},
            }
        )

    async with stub_source_upstreams() as start:
        url = await start(upstream)
        created = await async_client.post("/api/openrouter-accounts", json={"name": "Compact", "apiKey": "secret-test"})
        account_id = created.json()["id"]
        await async_client.patch(
            f"/api/openrouter-accounts/{account_id}", json={"selections": [{"model": "vendor/test"}]}
        )
        async with SessionLocal() as session:
            source = await session.get(ModelSource, account_id)
            assert source is not None
            source.base_url = url
            await session.commit()
        result = await async_client.post(
            path, json={"model": "openrouter/vendor/test", "instructions": "Summarize", "input": "Hello"}
        )
        assert result.status_code == 200, result.text
        body = result.json()
        assert body["object"] == "response.compaction"
        assert decode_codex_lb_compaction_summary(body["output"][0]["encrypted_content"]) == "Preserved summary"
