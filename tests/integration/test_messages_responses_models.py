from __future__ import annotations

import base64
import json

import pytest
from aiohttp import web
from sqlalchemy import select

import app.modules.proxy.service as proxy_module
from app.core.config.settings import Settings
from app.db.models import DashboardSettings, ModelSource, RequestLog
from app.db.session import SessionLocal
from app.modules.openrouter.client import OpenRouterClient
from app.modules.openrouter.schemas import CatalogResponse, KeyInfo
from tests.integration.model_source_helpers import stub_source_upstreams

pytestmark = pytest.mark.integration

SESSION = "33333333-3333-4333-8333-333333333333"
CLAUDE_CODE_HEADERS = {
    "user-agent": "claude-cli/2.1.90 (external, cli)",
    "anthropic-version": "2023-06-01",
    "x-claude-code-session-id": SESSION,
}


@pytest.fixture(autouse=True)
def _disable_http_bridge(monkeypatch: pytest.MonkeyPatch) -> None:
    app_settings = Settings(http_responses_session_bridge_enabled=False)
    dashboard_settings = DashboardSettings(
        id=1,
        sticky_threads_enabled=False,
        upstream_stream_transport="auto",
        prohibit_fast_mode=False,
        prefer_earlier_reset_accounts=False,
        routing_strategy="usage_weighted",
        openai_cache_affinity_max_age_seconds=300,
        import_without_overwrite=False,
        totp_required_on_login=False,
        api_key_auth_enabled=False,
        http_responses_session_bridge_prompt_cache_idle_ttl_seconds=3600,
        http_responses_session_bridge_gateway_safe_mode=False,
        sticky_reallocation_budget_threshold_pct=95.0,
    )

    class _SettingsCache:
        async def get(self) -> DashboardSettings:
            return dashboard_settings

    monkeypatch.setattr(proxy_module, "get_settings_cache", lambda: _SettingsCache())
    monkeypatch.setattr(proxy_module, "get_settings", lambda: app_settings)


def _jwt(payload: dict) -> str:
    return "header." + base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode() + ".sig"


async def _import_account(async_client) -> None:
    claims = {
        "email": "messages@example.test",
        "chatgpt_account_id": "acc_messages",
        "https://api.openai.com/auth": {"chatgpt_plan_type": "pro"},
    }
    auth = {
        "tokens": {
            "idToken": _jwt(claims),
            "accessToken": "access-token",
            "refreshToken": "refresh-token",
            "accountId": "acc_messages",
        }
    }
    files = {"auth_json": ("auth.json", json.dumps(auth), "application/json")}
    response = await async_client.post("/api/accounts/import", files=files)
    assert response.status_code == 200, response.text


def _upstream_turn(text: str, *, encrypted: str = "enc-1") -> list[dict]:
    return [
        {"type": "response.created", "response": {"id": "resp_turn", "object": "response", "status": "in_progress"}},
        {"type": "response.output_item.added", "output_index": 0, "item": {"id": "rs_turn", "type": "reasoning"}},
        {
            "type": "response.reasoning_summary_text.delta",
            "item_id": "rs_turn",
            "summary_index": 0,
            "delta": "Thinking",
        },
        {
            "type": "response.output_item.done",
            "output_index": 0,
            "item": {"id": "rs_turn", "type": "reasoning", "summary": [], "encrypted_content": encrypted},
        },
        {
            "type": "response.output_item.added",
            "output_index": 1,
            "item": {"id": "msg_turn", "type": "message", "role": "assistant", "phase": "final_answer"},
        },
        {"type": "response.output_text.delta", "item_id": "msg_turn", "output_index": 1, "delta": text},
        {
            "type": "response.output_item.done",
            "output_index": 1,
            "item": {
                "id": "msg_turn",
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": text}],
            },
        },
        {
            "type": "response.completed",
            "response": {
                "id": "resp_turn",
                "object": "response",
                "status": "completed",
                "output": [],
                "usage": {
                    "input_tokens": 1000,
                    "output_tokens": 20,
                    "total_tokens": 1020,
                    "input_tokens_details": {"cached_tokens": 600},
                },
            },
        },
    ]


def _messages_events(lines: list[str]) -> list[dict]:
    return [json.loads(line[6:]) for line in lines if line.startswith("data: ")]


async def test_claude_code_turns_served_by_native_account(async_client, monkeypatch):
    await _import_account(async_client)
    seen: list[dict] = []

    async def fake_stream(payload, headers, access_token, account_id, **kwargs):
        seen.append(payload.to_payload())
        for event in _upstream_turn("Hello"):
            yield f"data: {json.dumps(event)}\n\n"

    monkeypatch.setattr(proxy_module, "core_stream_responses", fake_stream)
    body = {
        "model": "gpt-5.4",
        "system": [
            {"type": "text", "text": "x-anthropic-billing-header: cc_version=2"},
            {"type": "text", "text": "Rules"},
        ],
        "messages": [{"role": "user", "content": "Hi"}],
        "max_tokens": 32000,
        "thinking": {"type": "adaptive"},
        "output_config": {"effort": "high"},
        "stream": True,
    }
    async with async_client.stream("POST", "/v1/messages", json=body, headers=CLAUDE_CODE_HEADERS) as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        events = _messages_events([line async for line in response.aiter_lines()])

    assert [event["type"] for event in events] == [
        "message_start",
        "content_block_start",
        "content_block_delta",
        "content_block_delta",
        "content_block_stop",
        "content_block_start",
        "content_block_delta",
        "content_block_stop",
        "message_delta",
        "message_stop",
    ]
    assert events[0]["message"]["model"] == "gpt-5.4"
    signature = events[3]["delta"]["signature"]
    assert signature.startswith("clb1:")
    assert events[6]["delta"] == {"type": "text_delta", "text": "Hello"}
    assert events[8]["usage"]["input_tokens"] == 400
    assert events[8]["usage"]["cache_read_input_tokens"] == 600
    upstream = seen[0]
    assert upstream["instructions"] == "Rules"
    assert upstream["reasoning"]["effort"] == "high"
    assert upstream["include"] == ["reasoning.encrypted_content"]
    first_cache_key = upstream["prompt_cache_key"]

    replay = {
        **body,
        "stream": False,
        "messages": [
            {"role": "user", "content": "Hi"},
            {
                "role": "assistant",
                "content": [
                    {"type": "thinking", "thinking": "Thinking", "signature": signature},
                    {"type": "text", "text": "Hello"},
                ],
            },
            {"role": "user", "content": "Again"},
        ],
    }
    response = await async_client.post("/v1/messages", json=replay, headers=CLAUDE_CODE_HEADERS)
    assert response.status_code == 200, response.text
    message = response.json()
    assert message["type"] == "message" and message["stop_reason"] == "end_turn"
    assert [block["type"] for block in message["content"]] == ["thinking", "text"]
    assert seen[1]["prompt_cache_key"] == first_cache_key
    assert {"type": "reasoning", "id": "rs_turn", "summary": [], "encrypted_content": "enc-1"} in [
        {key: item.get(key) for key in ("type", "id", "summary", "encrypted_content")}
        for item in seen[1]["input"]
        if item.get("type") == "reasoning"
    ]

    async with SessionLocal() as session:
        logs = list(await session.scalars(select(RequestLog).order_by(RequestLog.requested_at)))
    assert [(log.model, log.conversation_id, log.request_operation) for log in logs] == [
        ("gpt-5.4", SESSION, "messages"),
        ("gpt-5.4", SESSION, "messages"),
    ]


async def test_overflow_before_output_triggers_claude_code_compaction(async_client, monkeypatch):
    await _import_account(async_client)

    async def fake_stream(payload, headers, access_token, account_id, **kwargs):
        failed = {
            "type": "response.failed",
            "response": {
                "id": "resp_overflow",
                "status": "failed",
                "error": {"code": "context_length_exceeded", "message": "Your input exceeds the context window."},
            },
        }
        yield f"data: {json.dumps(failed)}\n\n"

    monkeypatch.setattr(proxy_module, "core_stream_responses", fake_stream)
    response = await async_client.post(
        "/v1/messages",
        json={"model": "gpt-5.4", "max_tokens": 10, "messages": [{"role": "user", "content": "Hi"}], "stream": True},
        headers=CLAUDE_CODE_HEADERS,
    )
    assert response.status_code == 400, response.text
    assert response.json() == {
        "type": "error",
        "error": {
            "type": "invalid_request_error",
            "message": "prompt is too long: Your input exceeds the context window.",
        },
    }


async def test_count_tokens_and_rejections_stay_local(async_client, monkeypatch):
    await _import_account(async_client)

    async def fake_stream(*args, **kwargs):
        raise AssertionError("no upstream request expected")
        yield ""

    monkeypatch.setattr(proxy_module, "core_stream_responses", fake_stream)
    counted = await async_client.post(
        "/v1/messages/count_tokens",
        json={"model": "gpt-5.4", "messages": [{"role": "user", "content": "Hello there"}]},
        headers=CLAUDE_CODE_HEADERS,
    )
    assert counted.status_code == 200, counted.text
    assert counted.json()["input_tokens"] > 0
    rejected = await async_client.post(
        "/v1/messages",
        json={
            "model": "gpt-5.4",
            "max_tokens": 10,
            "stop_sequences": ["END"],
            "messages": [{"role": "user", "content": "Hi"}],
        },
        headers=CLAUDE_CODE_HEADERS,
    )
    assert rejected.status_code == 400
    assert rejected.json()["error"]["type"] == "invalid_request_error"
    assert "stop_sequences" in rejected.json()["error"]["message"]


@pytest.fixture
def openrouter_catalog(monkeypatch):
    catalog = CatalogResponse.model_validate(
        {
            "data": [
                {
                    "id": "vendor/test",
                    "name": "Test model",
                    "context_length": 200_000,
                    "architecture": {"input_modalities": ["text"], "output_modalities": ["text"]},
                    "pricing": {"prompt": "0.000001", "completion": "0.000002"},
                    "top_provider": {"context_length": 200_000, "max_completion_tokens": 32000},
                    "supported_parameters": ["tools", "reasoning"],
                }
            ]
        }
    )

    async def key_info(self, key):
        return KeyInfo(usage=1, usage_daily=1, usage_weekly=1, usage_monthly=1, is_free_tier=False)

    async def models(self, key):
        return catalog

    monkeypatch.setattr(OpenRouterClient, "key_info", key_info)
    monkeypatch.setattr(OpenRouterClient, "catalog", models)


async def test_claude_code_request_served_by_openrouter_source(async_client, openrouter_catalog):
    requests: list[dict] = []

    async def upstream(request):
        body = await request.json()
        requests.append(body)
        call = {
            "id": "fc_1",
            "type": "function_call",
            "status": "completed",
            "call_id": "call_1",
            "name": body["tools"][0]["name"],
            "arguments": '{"path":"a.txt"}',
        }
        events = [
            {
                "type": "response.created",
                "response": {"id": "resp_source", "object": "response", "status": "in_progress", "output": []},
            },
            {"type": "response.output_item.added", "output_index": 0, "item": {**call, "arguments": ""}},
            {
                "type": "response.function_call_arguments.delta",
                "item_id": "fc_1",
                "output_index": 0,
                "delta": call["arguments"],
            },
            {"type": "response.output_item.done", "output_index": 0, "item": call},
            {
                "type": "response.completed",
                "response": {
                    "id": "resp_source",
                    "object": "response",
                    "status": "completed",
                    "output": [call],
                    "usage": {"input_tokens": 10, "output_tokens": 2, "total_tokens": 12, "cost": 0.001},
                },
            },
        ]
        text = "".join(f"data: {json.dumps(event)}\n\n" for event in events)
        return web.Response(text=text, content_type="text/event-stream")

    async with stub_source_upstreams() as start:
        url = await start(upstream)
        created = await async_client.post("/api/openrouter-accounts", json={"name": "OR", "apiKey": "secret-test"})
        account_id = created.json()["id"]
        await async_client.patch(
            f"/api/openrouter-accounts/{account_id}", json={"selections": [{"model": "vendor/test"}]}
        )
        async with SessionLocal() as session:
            source = await session.get(ModelSource, account_id)
            assert source is not None
            source.base_url = url
            await session.commit()
        response = await async_client.post(
            "/v1/messages",
            json={
                "model": "openrouter/vendor/test",
                "max_tokens": 1000,
                "tools": [
                    {"name": "Read", "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}}}
                ],
                "messages": [{"role": "user", "content": "Read a.txt"}],
            },
            headers=CLAUDE_CODE_HEADERS,
        )

    assert response.status_code == 200, response.text
    message = response.json()
    assert message["model"] == "openrouter/vendor/test"
    assert message["stop_reason"] == "tool_use"
    assert message["content"] == [{"type": "tool_use", "id": "call_1", "name": "Read", "input": {"path": "a.txt"}}]
    assert requests[0]["model"] == "vendor/test"
    assert requests[0]["input"] == [
        {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "Read a.txt"}]}
    ]
    async with SessionLocal() as session:
        log = (await session.scalars(select(RequestLog).where(RequestLog.model_source_id == account_id))).one()
    assert log.conversation_id == SESSION
    assert log.request_operation == "messages"
    assert log.cost_usd == pytest.approx(0.001)
