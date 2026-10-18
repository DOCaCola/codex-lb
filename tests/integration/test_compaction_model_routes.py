"""Native compaction requests run on the configured compaction model."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

import app.modules.proxy.service as proxy_module
from app.core.openai.models import OpenAIResponsePayload
from tests.integration.test_proxy_affinity_observation import _import_synthetic_account
from tests.integration.test_proxy_affinity_websocket_observation import SyntheticUpstream, seed_account

pytestmark = pytest.mark.integration

ROUTES_PATH = "/api/settings/model-compaction-routes"
TRIGGER_INPUT = [
    {"role": "user", "content": [{"type": "input_text", "text": "work"}]},
    {"type": "compaction_trigger"},
]


@pytest.mark.asyncio
async def test_settings_api_stores_compatible_routes_and_rejects_others(async_client):
    initial = await async_client.get(ROUTES_PATH)
    assert initial.status_code == 200
    assert initial.json()["routes"] == []
    models = {model["slug"]: model for model in initial.json()["models"]}
    assert "max" in models["gpt-5.6-luna"]["reasoningEfforts"]

    stored = await async_client.put(f"{ROUTES_PATH}/gpt-6-astra", json={"compactionModel": "gpt-5.6-luna"})
    assert stored.status_code == 200, stored.text
    assert stored.json()["routes"] == [
        {
            "slug": "gpt-6-astra",
            "compactionModel": "gpt-5.6-luna",
            "reasoningEffort": None,
            "status": "active",
            "reason": None,
        }
    ]
    updated = await async_client.put(
        f"{ROUTES_PATH}/gpt-6-astra", json={"compactionModel": "gpt-5.6-luna", "reasoningEffort": "max"}
    )
    assert updated.json()["routes"][0]["reasoningEffort"] == "max"

    mismatch = await async_client.put(f"{ROUTES_PATH}/gpt-5.6-sol", json={"compactionModel": "gpt-5.5"})
    assert mismatch.status_code == 400
    assert mismatch.json()["error"]["code"] == "compaction_route_incompatible"
    # Luna compacts Astra, so it cannot be routed itself.
    chained = await async_client.put(f"{ROUTES_PATH}/gpt-5.6-luna", json={"compactionModel": "gpt-5.6-terra"})
    assert chained.status_code == 400
    assert chained.json()["error"]["code"] == "compaction_route_incompatible"

    missing = await async_client.delete(f"{ROUTES_PATH}/gpt-5.6-sol")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "compaction_route_not_found"
    deleted = await async_client.delete(f"{ROUTES_PATH}/gpt-6-astra")
    assert deleted.status_code == 200
    assert deleted.json()["routes"] == []


@pytest.mark.asyncio
async def test_http_compaction_runs_on_the_compaction_model_and_turns_keep_theirs(async_client, monkeypatch):
    await _import_synthetic_account(async_client)
    stored = await async_client.put(
        f"{ROUTES_PATH}/gpt-6-astra", json={"compactionModel": "gpt-5.6-luna", "reasoningEffort": "max"}
    )
    assert stored.status_code == 200, stored.text
    sent: list[tuple[str, str | None]] = []

    async def stream(payload, *args, **kwargs):
        sent.append((payload.model, payload.reasoning.effort if payload.reasoning else None))
        yield 'data: {"type":"response.completed","response":{"id":"resp_route","status":"completed","output":[]}}\n\n'

    async def compact(payload, *args, **kwargs):
        sent.append((payload.model, payload.reasoning.effort if payload.reasoning else None))
        return OpenAIResponsePayload.model_validate({"output": []})

    monkeypatch.setattr(proxy_module, "core_stream_responses", stream)
    monkeypatch.setattr(proxy_module, "core_compact_responses", compact)
    requests = [
        ("/backend-api/codex/responses", TRIGGER_INPUT),
        ("/backend-api/codex/responses", TRIGGER_INPUT[:1]),
        ("/backend-api/codex/responses/compact", TRIGGER_INPUT[:1]),
    ]
    for path, items in requests:
        payload = {"model": "gpt-6-astra", "instructions": "", "input": items, "reasoning": {"effort": "high"}}
        if not path.endswith("compact"):
            payload["stream"] = True
        response = await async_client.post(path, json=payload)
        assert response.status_code == 200, response.text

    assert sent == [("gpt-5.6-luna", "max"), ("gpt-6-astra", "high"), ("gpt-5.6-luna", "max")]
    rows = (await async_client.get("/api/request-logs")).json()["requests"]
    assert sorted(row["model"] for row in rows) == ["gpt-5.6-luna", "gpt-5.6-luna", "gpt-6-astra"]


def test_websocket_compaction_runs_on_the_compaction_model(app_instance, monkeypatch):
    upstream = SyntheticUpstream()
    sent: list[dict] = []
    send_text = upstream.send_text

    async def record(text: str) -> None:
        sent.append(json.loads(text))
        await send_text(text)

    upstream.send_text = record

    async def connect(*args, **kwargs):
        return upstream

    monkeypatch.setattr(proxy_module, "connect_responses_websocket", connect)
    with TestClient(app_instance, client=("127.0.0.1", 50000)) as client:
        assert client.portal is not None
        key = client.portal.call(seed_account)
        stored = client.put(
            f"http://localhost{ROUTES_PATH}/gpt-6-astra",
            json={"compactionModel": "gpt-5.6-luna", "reasoningEffort": "low"},
        )
        assert stored.status_code == 200, stored.text
        with client.websocket_connect(
            "ws://localhost/backend-api/codex/responses", headers={"authorization": f"Bearer {key}"}
        ) as websocket:
            websocket.send_json(
                {
                    "type": "response.create",
                    "model": "gpt-6-astra",
                    "input": TRIGGER_INPUT,
                    "reasoning": {"effort": "high"},
                }
            )
            assert websocket.receive_json()["type"] == "response.created"
            assert websocket.receive_json()["type"] == "response.completed"
        assert client.portal.call(app_instance.state.proxy_service.drain_persistence_tasks, 5.0)
        rows = client.get("http://localhost/api/request-logs").json()["requests"]

    assert [(request["model"], request["reasoning"]["effort"]) for request in sent] == [("gpt-5.6-luna", "low")]
    assert [row["model"] for row in rows] == ["gpt-5.6-luna"]
