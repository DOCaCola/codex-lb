from __future__ import annotations

import base64
import json

import pytest
from aiohttp import web
from sqlalchemy import select

from app.db.models import ModelSource, RequestLog, SourceCooldown
from app.db.session import SessionLocal
from app.modules.model_sources import pooled_accounts
from app.modules.openai_api.client import OpenAIApiClient, OpenAIApiError
from app.modules.openai_api.schemas import UpstreamModel
from tests.integration.model_source_helpers import stub_source_upstreams

pytestmark = pytest.mark.integration

TEXT_MODEL = "openai-apikey/gpt-5.5"
IMAGE_MODEL = "openai-apikey/gpt-image-2.5-sunburst"


@pytest.fixture
def platform(monkeypatch):
    models = [
        UpstreamModel(id=model_id)
        for model_id in ("gpt-5.5", "gpt-image-2.5-sunburst", "text-embedding-3-small", "whisper-1", "tts-1")
    ]

    async def list_models(self, key):
        if key == "invalid":
            raise OpenAIApiError("OpenAI /models returned HTTP 401")
        return models

    monkeypatch.setattr(OpenAIApiClient, "models", list_models)
    pooled_accounts._rotation.clear()
    return models


async def _account(async_client, name: str, url: str | None = None, **settings) -> str:
    created = await async_client.post("/api/openai-api-accounts", json={"name": name, "apiKey": "sk-test", **settings})
    assert created.status_code == 200, created.text
    account_id = created.json()["id"]
    selected = await async_client.patch(
        f"/api/openai-api-accounts/{account_id}",
        json={"selections": [{"model": "gpt-5.5"}, {"model": "gpt-image-2.5-sunburst"}]},
    )
    assert selected.status_code == 200, selected.text
    if url is not None:
        async with SessionLocal() as session:
            source = await session.get(ModelSource, account_id)
            assert source is not None
            source.base_url = url
            await session.commit()
    return account_id


async def test_account_lifecycle_catalog_and_client_lists(async_client, platform):
    rejected = await async_client.post("/api/openai-api-accounts", json={"name": "Bad", "apiKey": "invalid"})
    assert rejected.status_code == 400
    assert "invalid" not in rejected.text

    created = await async_client.post(
        "/api/openai-api-accounts",
        json={"name": "Platform", "apiKey": "sk-test", "monthlyCreditUsd": 50, "creditRenewsOn": 31},
    )
    assert created.status_code == 200, created.text
    assert "sk-test" not in created.text
    account = created.json()
    assert account["state"]["selections"] == []
    assert account["state"]["catalog_updated_at"].endswith("Z")
    assert [(model["id"], model["kind"]) for model in account["state"]["catalog"]] == [
        ("gpt-image-2.5-sunburst", "image"),
        ("gpt-5.5", "text"),
    ]
    assert account["credit"]["monthlyCreditUsd"] == 50
    assert account["credit"]["spentUsd"] == 0
    assert account["credit"]["remainingUsd"] == 50

    unknown = await async_client.patch(
        f"/api/openai-api-accounts/{account['id']}", json={"selections": [{"model": "whisper-1"}]}
    )
    assert unknown.status_code == 400
    await _account(async_client, "Second")

    models = (await async_client.get("/v1/models")).json()["data"]
    by_id = {model["id"]: model for model in models}
    assert by_id[TEXT_MODEL]["api_types"] == ["chat_completions"]
    assert by_id[IMAGE_MODEL]["api_types"] == ["images"]
    codex = (await async_client.get("/backend-api/codex/models")).json()
    codex_slugs = {model["slug"] for model in codex["models"]}
    assert TEXT_MODEL not in codex_slugs
    assert IMAGE_MODEL not in codex_slugs

    cleared = await async_client.patch(f"/api/openai-api-accounts/{account['id']}", json={"monthlyCreditUsd": None})
    assert cleared.json()["credit"]["remainingUsd"] is None


async def test_responses_project_model_and_codex_routes_refuse(async_client, platform):
    calls = []

    async def upstream(request):
        body = await request.json()
        calls.append(body)
        return web.json_response(
            {
                "id": "resp_api",
                "object": "response",
                "status": "completed",
                "output": [],
                "usage": {"input_tokens": 1000, "output_tokens": 100, "total_tokens": 1100},
            }
        )

    async with stub_source_upstreams() as start:
        account_id = await _account(async_client, "Platform", await start(upstream))
        result = await async_client.post("/v1/responses", json={"model": TEXT_MODEL, "input": "Hi", "stream": False})
        assert result.status_code == 200, result.text
        assert calls[0]["model"] == "gpt-5.5"
        assert calls[0]["store"] is False

        image_on_text = await async_client.post(
            "/v1/responses", json={"model": IMAGE_MODEL, "input": "Hi", "stream": False}
        )
        assert image_on_text.status_code == 400
        codex = await async_client.post(
            "/backend-api/codex/responses", json={"model": TEXT_MODEL, "input": "Hi", "stream": False}
        )
        assert codex.status_code == 400, codex.text
        assert codex.json()["error"]["code"] == "unsupported_model"
        assert len(calls) == 1

        async with SessionLocal() as session:
            costs = list(
                await session.scalars(select(RequestLog.cost_usd).where(RequestLog.model_source_id == account_id))
            )
        assert costs == [pytest.approx(1000 / 1e6 * 5 + 100 / 1e6 * 30)]
        account = (await async_client.get("/api/openai-api-accounts")).json()["accounts"][0]
        assert account["credit"]["spentUsd"] == pytest.approx(costs[0])


async def test_billing_exhaustion_fails_over_until_refresh(async_client, platform):
    calls = []

    async def exhausted(request):
        calls.append("exhausted")
        return web.json_response(
            {
                "error": {
                    "message": "You exceeded your current quota",
                    "type": "insufficient_quota",
                    "code": "insufficient_quota",
                }
            },
            status=429,
        )

    async def funded(request):
        calls.append("funded")
        return web.json_response(
            {
                "id": "resp_funded",
                "object": "response",
                "status": "completed",
                "output": [],
                "usage": {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2},
            }
        )

    async with stub_source_upstreams() as start:
        first = await _account(async_client, "A", await start(exhausted), creditRenewsOn=1)
        await _account(async_client, "B", await start(funded))
        for _ in range(2):
            result = await async_client.post(
                "/v1/responses", json={"model": TEXT_MODEL, "input": "Hi", "stream": False}
            )
            assert result.status_code == 200, result.text
        assert calls == ["exhausted", "funded", "funded"]
        async with SessionLocal() as session:
            cooldown = (await session.scalars(select(SourceCooldown).where(SourceCooldown.source_id == first))).one()
        assert cooldown.model == "*"
        assert (cooldown.until.day, cooldown.until.hour) == (1, 0)
        listed = {
            account["id"]: account
            for account in (await async_client.get("/api/openai-api-accounts")).json()["accounts"]
        }
        assert listed[first]["credit"]["exhaustedUntil"] is not None

        refreshed = await async_client.post(f"/api/openai-api-accounts/{first}/refresh")
        assert refreshed.status_code == 200, refreshed.text
        assert refreshed.json()["credit"]["exhaustedUntil"] is None


async def test_redirect_settings_offer_client_and_disabled_requested_models(async_client, platform):
    created = await async_client.post("/api/openai-api-accounts", json={"name": "Platform", "apiKey": "sk-test"})
    assert created.status_code == 200, created.text

    settings = (await async_client.get("/api/settings/model-redirects")).json()
    assert settings["imageSources"] == ["gpt-image-2"]
    # The catalogue's text model is offered while disabled; its image model is never a requested model.
    assert settings["disabledModels"] == [
        {
            "provider": "openai_apikey",
            "models": [{"slug": TEXT_MODEL, "displayName": "gpt-5.5", "hidden": False, "image": False}],
        }
    ]

    selected = await async_client.patch(
        f"/api/openai-api-accounts/{created.json()['id']}", json={"selections": [{"model": "gpt-5.5"}]}
    )
    assert selected.status_code == 200, selected.text
    settings = (await async_client.get("/api/settings/model-redirects")).json()
    assert settings["disabledModels"] == []
    assert TEXT_MODEL in [target["slug"] for group in settings["targets"] for target in group["models"]]


async def test_image_redirect_serves_codex_image_backend(async_client, platform):
    calls = []
    png = base64.b64encode(b"png").decode()

    async def upstream(request):
        calls.append((request.path, await request.json()))
        return web.json_response(
            {"created": 1, "data": [{"b64_json": png}], "usage": {"input_tokens": 10, "output_tokens": 1000}}
        )

    async with stub_source_upstreams() as start:
        account_id = await _account(async_client, "Platform", await start(upstream))
        mixed = await async_client.put("/api/settings/model-redirects/gpt-image-2", json={"targetModel": "gpt-5.5"})
        assert mixed.status_code == 400
        mixed = await async_client.put("/api/settings/model-redirects/gpt-5.4", json={"targetModel": IMAGE_MODEL})
        assert mixed.status_code == 400
        stored = await async_client.put("/api/settings/model-redirects/gpt-image-2", json={"targetModel": IMAGE_MODEL})
        assert stored.status_code == 200, stored.text
        assert {"slug": IMAGE_MODEL, "displayName": "gpt-image-2.5-sunburst", "hidden": False, "image": True} in [
            target for group in stored.json()["targets"] for target in group["models"]
        ]

        result = await async_client.post(
            "/backend-api/codex/images/generations", json={"model": "gpt-image-2", "prompt": "A sunburst"}
        )
        assert result.status_code == 200, result.text
        assert result.json()["data"][0]["b64_json"] == png
        edit = await async_client.post(
            "/v1/images/edits",
            data={"model": IMAGE_MODEL, "prompt": "Brighter"},
            files={"image": ("in.png", b"input", "image/png")},
        )
        assert edit.status_code == 200, edit.text
        assert calls[0] == ("/v1/images/generations", {"model": "gpt-image-2.5-sunburst", "prompt": "A sunburst"})
        assert calls[1][0] == "/v1/images/edits"
        assert calls[1][1]["model"] == "gpt-image-2.5-sunburst"
        assert calls[1][1]["images"] == [{"image_url": "data:image/png;base64," + base64.b64encode(b"input").decode()}]

        async with SessionLocal() as session:
            logs = list(await session.scalars(select(RequestLog).where(RequestLog.model_source_id == account_id)))
        assert [(log.model, log.requested_model) for log in logs] == [(IMAGE_MODEL, "gpt-image-2"), (IMAGE_MODEL, None)]
        assert logs[0].cost_usd == pytest.approx(10 / 1e6 * 5 + 1000 / 1e6 * 30)


async def test_image_stream_passes_through(async_client, platform):
    frames = [
        {"type": "image_generation.partial_image", "b64_json": "cGFy", "partial_image_index": 0},
        {
            "type": "image_generation.completed",
            "b64_json": "ZG9uZQ==",
            "usage": {"input_tokens": 4, "output_tokens": 8},
        },
    ]
    wire = "".join(f"event: {frame['type']}\ndata: {json.dumps(frame)}\n\n" for frame in frames).encode()

    async def upstream(request):
        response = web.StreamResponse(headers={"Content-Type": "text/event-stream"})
        await response.prepare(request)
        await response.write(wire)
        await response.write_eof()
        return response

    async with stub_source_upstreams() as start:
        account_id = await _account(async_client, "Platform", await start(upstream))
        result = await async_client.post(
            "/v1/images/generations", json={"model": IMAGE_MODEL, "prompt": "Stream", "stream": True}
        )
        assert result.status_code == 200, result.text
        assert result.content == wire
        async with SessionLocal() as session:
            log = (await session.scalars(select(RequestLog).where(RequestLog.model_source_id == account_id))).one()
        assert (log.status, log.input_tokens, log.output_tokens) == ("success", 4, 8)
