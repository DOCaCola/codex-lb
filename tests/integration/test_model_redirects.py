from __future__ import annotations

import asyncio
import json
from dataclasses import replace
from urllib.parse import quote

import pytest
from aiohttp import web
from fastapi.testclient import TestClient
from sqlalchemy import update

import app.modules.proxy.service as proxy_module
from app.core.openai.model_redirects import get_model_redirects_cache
from app.core.openai.model_registry import get_model_registry
from app.core.openai.models import OpenAIResponsePayload
from app.db.models import ModelRedirect
from app.db.session import SessionLocal
from app.modules.proxy.request_policy import resolve_request_model
from tests.integration.model_source_helpers import _create_model_source, _enable_api_key_auth, stub_source_upstreams
from tests.integration.test_compaction_model_routes import TRIGGER_INPUT
from tests.integration.test_messages_responses_models import _upstream_turn
from tests.integration.test_proxy_affinity_observation import _import_synthetic_account
from tests.integration.test_proxy_affinity_websocket_observation import SyntheticUpstream, seed_account
from tests.integration.test_settings_audit_changed_fields import _wait_for_settings_changed_audit_log
from tests.integration.test_v1_models import _make_upstream_model

pytestmark = pytest.mark.integration
REDIRECTS_PATH = "/api/settings/model-redirects"
COMPACTION_PATH = "/api/settings/model-compaction-routes"
CATALOGUE_PATH = "/api/settings/model-context-window-overrides"


def _redirect_path(source: str) -> str:
    return f"{REDIRECTS_PATH}/{quote(source, safe='')}"


async def _redirect(client, source: str, target: str):
    response = await client.put(_redirect_path(source), json={"targetModel": target})
    assert response.status_code == 200, response.text
    return response.json()


async def test_redirect_settings_validate_writes_and_audit(async_client):
    stored = await _redirect(async_client, "old/vendor-model", "gpt-6-astra")
    assert stored["redirects"] == [
        {"sourceModel": "old/vendor-model", "targetModel": "gpt-6-astra", "status": "active", "reason": None}
    ]
    assert any(group["provider"] == "subscription" for group in stored["targets"])
    audit = await _wait_for_settings_changed_audit_log()
    assert audit.details is not None
    assert json.loads(audit.details) == {
        "changed_fields": ["model_redirects"],
        "slug": "old/vendor-model",
        "target_model": "gpt-6-astra",
    }
    for source, target in (
        ("invalid slug", "gpt-6-astra"),
        ("gpt-6-astra", "gpt-6-astra"),
        ("another-old", "old/vendor-model"),
        ("gpt-6-astra", "gpt-5.6-luna"),
        ("another-old", "unknown-target"),
    ):
        result = await async_client.put(_redirect_path(source), json={"targetModel": target})
        assert result.status_code == 400, result.text
        assert result.json()["error"]["code"] == "model_redirect_invalid"
        assert result.json()["error"]["message"]

    wrong_case = await async_client.put(_redirect_path("new"), json={"target_model": "gpt-6-astra"})
    assert wrong_case.status_code == 422
    replaced = await _redirect(async_client, "old/vendor-model", "gpt-5.6-luna")
    assert replaced["redirects"][0]["targetModel"] == "gpt-5.6-luna"
    deleted = await async_client.delete(_redirect_path("old/vendor-model"))
    assert deleted.status_code == 200
    assert deleted.json()["redirects"] == []
    absent = await async_client.delete(_redirect_path("old/vendor-model"))
    assert absent.status_code == 404
    assert absent.json()["error"]["code"] == "model_redirect_not_found"


async def test_redirect_and_compaction_conflicts_are_rejected_by_both_apis(async_client):
    source, target = "gpt-6-astra", "gpt-5.6-luna"
    await _redirect(async_client, source, target)
    options = (await async_client.get(COMPACTION_PATH)).json()["models"]
    assert source not in {option["slug"] for option in options}
    for coding, compaction in ((source, target), (target, source)):
        result = await async_client.put(f"{COMPACTION_PATH}/{coding}", json={"compactionModel": compaction})
        assert result.status_code == 400
        assert result.json()["error"]["code"] == "model_redirect_conflict"

    assert (await async_client.delete(_redirect_path(source))).status_code == 200
    result = await async_client.put(f"{COMPACTION_PATH}/{source}", json={"compactionModel": target})
    assert result.status_code == 200, result.text
    for conflict in (source, target):
        result = await async_client.put(_redirect_path(conflict), json={"targetModel": "gpt-5.5"})
        assert result.status_code == 400
        assert result.json()["error"]["code"] == "model_redirect_conflict"
    # As a redirect target, a coding model still gets its configured compaction route.
    await _redirect(async_client, "legacy-coding-model", source)


async def test_concurrent_redirect_writes_cannot_build_a_chain(async_client):
    first, second = await asyncio.gather(
        async_client.put(_redirect_path("gpt-6-astra"), json={"targetModel": "gpt-5.6-luna"}),
        async_client.put(_redirect_path("gpt-5.6-luna"), json={"targetModel": "gpt-5.5"}),
    )
    assert sorted((first.status_code, second.status_code)) == [200, 400]
    assert len((await async_client.get(REDIRECTS_PATH)).json()["redirects"]) == 1


async def test_catalog_redirect_metadata_visibility_and_lifecycle(async_client):
    source = replace(_make_upstream_model("test-catalog-old"), display_name="Original name")
    target = replace(_make_upstream_model("test-catalog-new", base_instructions="Served instructions"), priority=7)
    await get_model_registry().update({"pro": [source, target]})
    assert (await async_client.put(f"{CATALOGUE_PATH}/{source.slug}", json={"contextWindow": 1000})).status_code == 200
    assert (await async_client.put(f"{CATALOGUE_PATH}/{target.slug}", json={"contextWindow": 2345})).status_code == 200
    await _redirect(async_client, source.slug, target.slug)
    retired = "retired/catalog-slug"
    await _redirect(async_client, retired, target.slug)

    codex = (await async_client.get("/backend-api/codex/models")).json()
    entries = {row["slug"]: row for row in codex["models"]}
    assert entries[source.slug] == {**entries[target.slug], "slug": source.slug, "display_name": "Original name"}
    assert entries[retired] == {**entries[target.slug], "slug": retired, "display_name": retired, "visibility": "hide"}
    assert entries[source.slug]["context_window"] == 2345
    assert entries[source.slug]["base_instructions"] == "Served instructions"
    assert retired not in {row["id"] for row in codex["data"]}

    dashboard = (await async_client.get(CATALOGUE_PATH)).json()
    retired_row = next(row for row in dashboard["models"] if row["slug"] == retired)
    assert retired_row["retired"] and not retired_row["listed"]
    assert retired_row["redirectTargetModel"] == target.slug
    assert retired_row["redirectTargetOverrideTokens"] == 2345
    assert (await async_client.delete(f"/api/settings/hidden-models/{quote(retired, safe='')}")).status_code == 200
    assert (await async_client.put(f"{CATALOGUE_PATH}/{source.slug}", json={"contextWindow": 2222})).status_code == 400
    openai = (await async_client.get("/v1/models")).json()
    assert next(row for row in openai["data"] if row["id"] == retired)["context_length"] == 2345
    anthropic = (await async_client.get("/v1/models", headers={"anthropic-version": "2023-06-01"})).json()
    assert next(row for row in anthropic["data"] if row["id"] == retired)["max_input_tokens"] == 2345

    await get_model_registry().update({"pro": [source]})
    inactive = (await async_client.get(REDIRECTS_PATH)).json()["redirects"]
    assert {row["reason"] for row in inactive} == {"model_redirect_target_unavailable"}
    assert {row["status"] for row in inactive} == {"inactive"}
    codex = (await async_client.get("/backend-api/codex/models")).json()
    assert {source.slug, retired}.isdisjoint(row["slug"] for row in codex["models"])

    assert (await async_client.delete(_redirect_path(source.slug))).status_code == 200
    codex = (await async_client.get("/backend-api/codex/models")).json()
    assert next(row for row in codex["models"] if row["slug"] == source.slug)["context_window"] == 1000


async def test_catalog_filters_redirected_source_by_the_keys_normalized_requested_slug(async_client):
    source, target = "gpt-5.4", "external-text-model"
    await _create_model_source(
        async_client, name="catalogue-source", model=target, base_url="http://127.0.0.1:9/v1", supports_responses=True
    )
    await _redirect(async_client, source, target)
    await _enable_api_key_auth(async_client)
    key = await async_client.post(
        "/api/api-keys/",
        json={"name": "alias", "allowedModels": [f"{source}-high"], "enforcedModel": f"{source}-high"},
    )
    assert key.status_code == 200, key.text
    headers = {"Authorization": f"Bearer {key.json()['key']}"}
    for url, extra_headers in (
        ("/v1/models", {}),
        ("/v1/models", {"anthropic-version": "2023-06-01"}),
        ("/backend-api/codex/models", {}),
    ):
        response = await async_client.get(url, headers={**headers, **extra_headers})
        assert response.status_code == 200, response.text
        assert [model["id"] for model in response.json()["data"]] == [source]


@pytest.mark.parametrize(
    ("path", "body"),
    [
        ("/backend-api/codex/responses", {"input": "hi"}),
        ("/backend-api/codex/responses/compact", {"input": "hi", "instructions": ""}),
        ("/v1/responses", {"input": "hi"}),
        ("/v1/responses/compact", {"input": "hi", "instructions": ""}),
        ("/v1/chat/completions", {"messages": [{"role": "user", "content": "hi"}]}),
        ("/v1/messages", {"messages": [{"role": "user", "content": "hi"}], "max_tokens": 100}),
        ("/v1/messages/count_tokens", {"messages": [{"role": "user", "content": "hi"}]}),
    ],
)
async def test_inactive_redirect_refuses_each_http_surface(async_client, path, body):
    source, target = "retired-invalid", "transient-redirect-target"
    survivor = _make_upstream_model("another-model")
    await get_model_registry().update({"pro": [_make_upstream_model(target), survivor]})
    await _redirect(async_client, source, target)
    await get_model_registry().update({"pro": [survivor]})
    response = await async_client.post(path, json={"model": source, **body})
    assert response.status_code == 400, response.text
    error = response.json()["error"]
    assert error["code"] == "model_redirect_target_unavailable"
    assert source in error["message"] and target in error["message"]


async def test_chained_out_of_band_targets_are_unavailable(async_client):
    await _redirect(async_client, "legacy", "gpt-6-astra")
    await _redirect(async_client, "gpt-5.6-sol", "gpt-5.5")
    async with SessionLocal() as session:
        await session.execute(
            update(ModelRedirect).where(ModelRedirect.source_model == "legacy").values(target_model="gpt-5.6-sol")
        )
        await session.commit()
    await get_model_redirects_cache().invalidate(propagate=False)
    rows = (await async_client.get(REDIRECTS_PATH)).json()["redirects"]
    assert next(row for row in rows if row["sourceModel"] == "legacy")["reason"] == "model_redirect_target_redirected"
    response = await async_client.post("/v1/responses", json={"model": "legacy", "input": "hi"})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "model_redirect_target_unavailable"


async def test_redirect_cache_retains_last_snapshot_when_reload_fails(async_client, monkeypatch):
    await _redirect(async_client, "legacy-cache-model", "gpt-6-astra")
    assert (await resolve_request_model("legacy-cache-model", None)).model == "gpt-6-astra"
    cache = get_model_redirects_cache()
    await cache.invalidate(propagate=False)

    async def unavailable(_session):
        raise RuntimeError("Temporary database outage")

    monkeypatch.setattr(cache, "_load", unavailable)
    resolution = await resolve_request_model("legacy-cache-model", None)
    assert (resolution.requested_model, resolution.model) == ("legacy-cache-model", "gpt-6-astra")


async def test_redirected_native_turns_compact_on_served_model_and_log_both(async_client, monkeypatch):
    await _import_synthetic_account(async_client)
    result = await async_client.put(
        f"{COMPACTION_PATH}/gpt-6-astra", json={"compactionModel": "gpt-5.6-luna", "reasoningEffort": "max"}
    )
    assert result.status_code == 200, result.text
    await _redirect(async_client, "legacy-coding-model", "gpt-6-astra")
    seen = []

    async def stream(payload, *args, **kwargs):
        seen.append((payload.model, payload.reasoning.effort if payload.reasoning else None))
        for event in _upstream_turn("redirected"):
            if "response" in event:
                event["response"]["model"] = payload.model
            yield f"data: {json.dumps(event)}\n\n"

    async def compact(payload, *args, **kwargs):
        seen.append((payload.model, payload.reasoning.effort if payload.reasoning else None))
        return OpenAIResponsePayload.model_validate({"output": []})

    monkeypatch.setattr(proxy_module, "core_stream_responses", stream)
    monkeypatch.setattr(proxy_module, "core_compact_responses", compact)
    for path, extra in (
        ("/backend-api/codex/responses", {"input": TRIGGER_INPUT, "stream": True}),
        ("/backend-api/codex/responses", {"input": "hi", "stream": False}),
        ("/backend-api/codex/responses/compact", {"input": "hi"}),
        ("/v1/responses", {"input": "hi"}),
        ("/v1/messages", {"messages": [{"role": "user", "content": "hi"}], "max_tokens": 100}),
        ("/v1/messages/count_tokens", {"messages": [{"role": "user", "content": "hi"}]}),
    ):
        response = await async_client.post(path, json={"model": "legacy-coding-model", "instructions": "", **extra})
        assert response.status_code == 200, response.text
        assert "openai-model" not in response.headers
        if path == "/v1/messages":
            assert response.json()["model"] == "gpt-6-astra"
    assert seen == [
        ("gpt-5.6-luna", "max"),
        ("gpt-6-astra", None),
        ("gpt-5.6-luna", "max"),
        ("gpt-6-astra", None),
        ("gpt-6-astra", None),
    ]
    rows = (await async_client.get("/api/request-logs", params={"model": "legacy-coding-model"})).json()["requests"]
    assert {row["model"] for row in rows} == {"gpt-5.6-luna", "gpt-6-astra"}
    assert {row["requestedModel"] for row in rows} == {"legacy-coding-model"}
    served_rows = (await async_client.get("/api/request-logs", params={"model": "gpt-5.6-luna"})).json()["requests"]
    assert len(served_rows) == 2
    options = (await async_client.get("/api/request-logs/options")).json()["modelOptions"]
    assert {"model": "legacy-coding-model", "reasoningEffort": "max"} in options


async def test_chat_uses_key_enforced_redirect_target_and_authorizes_the_source(async_client):
    source, target = "retired-chat-model", "external-chat-target"
    seen = []

    async def upstream(request: web.Request) -> web.Response:
        body = await request.json()
        seen.append(body["model"])
        return web.json_response(
            {
                "id": "chatcmpl-redirect",
                "object": "chat.completion",
                "created": 1,
                "model": body["model"],
                "choices": [{"index": 0, "message": {"role": "assistant", "content": "ok"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 3, "completion_tokens": 1, "total_tokens": 4},
            },
            headers={"OpenAI-Model": body["model"]},
        )

    async with stub_source_upstreams() as start:
        await _create_model_source(
            async_client,
            name="redirect-upstream",
            model=target,
            base_url=await start(upstream),
            input_per_1m=100.0,
            output_per_1m=100.0,
        )
        await _redirect(async_client, source, target)
        await _enable_api_key_auth(async_client)
        accepted = (
            await async_client.post(
                "/api/api-keys/",
                json={
                    "name": "retired",
                    "allowedModels": [source],
                    "enforcedModel": source,
                },
            )
        ).json()["key"]
        rejected = (
            await async_client.post(
                "/api/api-keys/",
                json={
                    "name": "target only",
                    "allowedModels": [target],
                },
            )
        ).json()["key"]
        payload = {"model": "ignored-by-key", "messages": [{"role": "user", "content": "hi"}]}
        response = await async_client.post(
            "/v1/chat/completions",
            json=payload,
            headers={
                "Authorization": f"Bearer {accepted}",
            },
        )
        assert response.status_code == 200, response.text
        assert response.json()["model"] == target
        assert "openai-model" not in response.headers
        denial = await async_client.post(
            "/v1/chat/completions",
            json={**payload, "model": source},
            headers={
                "Authorization": f"Bearer {rejected}",
            },
        )
        assert denial.status_code == 403
        assert seen == [target]
        rows = (await async_client.get("/api/request-logs", params={"modelOption": source})).json()["requests"]
        assert len(rows) == 1
        assert (rows[0]["model"], rows[0]["requestedModel"], rows[0]["costUsd"]) == (target, source, 0.0004)


@pytest.mark.parametrize("path", ["/backend-api/codex/responses", "/v1/responses"])
def test_websocket_resolves_redirect_after_suffix_alias(app_instance, monkeypatch, path):
    sent = []

    class CapturingUpstream(SyntheticUpstream):
        async def send_text(self, text: str) -> None:
            sent.append(json.loads(text))
            await super().send_text(text)

    async def connect(*args, **kwargs):
        return CapturingUpstream()

    monkeypatch.setattr(proxy_module, "connect_responses_websocket", connect)
    with TestClient(app_instance, client=("127.0.0.1", 50000)) as client:
        assert client.portal is not None
        key = client.portal.call(seed_account)
        stored = client.put(f"http://localhost{_redirect_path('gpt-5.4')}", json={"targetModel": "gpt-6-astra"})
        assert stored.status_code == 200, stored.text
        with client.websocket_connect(f"ws://localhost{path}", headers={"Authorization": f"Bearer {key}"}) as ws:
            assert ws.extra_headers is not None
            assert all(name.lower() != b"openai-model" for name, _ in ws.extra_headers)
            ws.send_json({"type": "response.create", "model": "gpt-5.4-high", "input": "synthetic websocket"})
            assert ws.receive_json()["type"] == "response.created"
            assert ws.receive_json()["type"] == "response.completed"
        assert client.portal.call(app_instance.state.proxy_service.drain_persistence_tasks, 5.0)
        rows = client.get("http://localhost/api/request-logs", params={"model": "gpt-5.4"}).json()["requests"]

    assert [(row["model"], row["reasoning"]["effort"]) for row in sent] == [("gpt-6-astra", "high")]
    assert [(row["model"], row["requestedModel"]) for row in rows] == [("gpt-6-astra", "gpt-5.4")]
