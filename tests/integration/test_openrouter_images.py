from __future__ import annotations

import asyncio
import base64
import json

import pytest
from aiohttp import web
from sqlalchemy import select

from app.db.models import ApiKeyUsageReservation, ModelSource, RequestLog
from app.db.session import SessionLocal
from app.modules.openrouter.client import OpenRouterClient
from app.modules.openrouter.schemas import (
    CatalogModel,
    CatalogResponse,
    ImageEndpoints,
    ImageModel,
    KeyInfo,
    ModelPricing,
    TopProvider,
)
from tests.integration.model_source_helpers import _AsgiStream, _enable_api_key_auth, stub_source_upstreams

pytestmark = pytest.mark.integration
MODEL = "openrouter/openai/gpt-image-2.5-sunburst"
IMAGE = "aGVsbG8="
USAGE = {"prompt_tokens": 10, "completion_tokens": 20, "cost": 0.012}


@pytest.fixture
def image_provider(monkeypatch):
    image = ImageModel.model_validate(
        {
            "id": MODEL.removeprefix("openrouter/"),
            "name": "Sunburst",
            "architecture": {"input_modalities": ["text", "image"], "output_modalities": ["image"]},
            "supports_streaming": True,
            "supported_parameters": {
                "n": {"type": "range", "min": 1, "max": 10},
                "input_references": {"type": "range", "min": 0, "max": 16},
                "quality": {"type": "enum", "values": ["auto", "high", "max"]},
            },
        }
    )
    endpoints = ImageEndpoints.model_validate(
        {
            "id": image.id,
            "endpoints": [
                {
                    "provider_name": "OpenAI",
                    "provider_slug": "openai",
                    "provider_tag": "openai",
                    "supports_streaming": True,
                    "supported_parameters": image.model_dump()["supported_parameters"],
                    "pricing": [{"billable": "output_image", "unit": "token", "cost_usd": 0.00003}],
                }
            ],
        }
    )
    catalog = CatalogResponse(
        data=[
            CatalogModel(
                id=image.id,
                name=image.name,
                architecture=image.architecture,
                image=image,
                pricing=ModelPricing(),
                top_provider=TopProvider(),
            )
        ]
    )

    async def get_catalog(self, key):
        return catalog.model_copy(deep=True)

    async def get_endpoints(self, key, model):
        return endpoints

    async def get_key(self, key):
        return KeyInfo(usage=0, usage_daily=0, usage_weekly=0, usage_monthly=0, is_free_tier=False)

    monkeypatch.setattr(OpenRouterClient, "catalog", get_catalog)
    monkeypatch.setattr(OpenRouterClient, "image_endpoints", get_endpoints)
    monkeypatch.setattr(OpenRouterClient, "key_info", get_key)
    return catalog


async def create_account(client, url):
    result = await client.post("/api/openrouter-accounts", json={"name": "Images", "apiKey": "image-secret"})
    assert result.status_code == 200, result.text
    account_id = result.json()["id"]
    selected = await client.patch(
        f"/api/openrouter-accounts/{account_id}", json={"selections": [{"model": MODEL.removeprefix("openrouter/")}]}
    )
    assert selected.status_code == 200, selected.text
    async with SessionLocal() as session:
        source = await session.get(ModelSource, account_id)
        source.base_url = url
        await session.commit()
    return account_id


@pytest.mark.parametrize("stream", [False, True])
@pytest.mark.parametrize("operation", ["generations", "edits"])
async def test_images_roundtrip_accounting_and_discovery(async_client, image_provider, stream, operation):
    requests = []

    async def upstream(request):
        assert request.path == "/v1/images"
        assert request.headers["Authorization"] == "Bearer image-secret"
        body = await request.json()
        requests.append(body)
        if not stream:
            return web.json_response({"created": 1, "data": [{"b64_json": IMAGE}], "usage": USAGE})
        events = [
            {"type": "image_generation.partial_image", "partial_image_index": 0, "b64_json": IMAGE},
            {"type": "image_generation.completed", "created": 1, "b64_json": IMAGE, "usage": USAGE},
        ]
        return web.Response(
            text="".join(f"data: {json.dumps(event)}\r\n\r\n" for event in events) + "data: [DONE]\n\n",
            content_type="text/event-stream",
        )

    async with stub_source_upstreams() as start:
        account_id = await create_account(async_client, await start(upstream))
        models = (await async_client.get("/v1/models")).json()["data"]
        entry = next(model for model in models if model["id"] == MODEL)
        assert entry["api_types"] == ["images"]
        assert "context_length" not in entry
        assert MODEL not in {
            model["slug"] for model in (await async_client.get("/backend-api/codex/models")).json()["models"]
        }
        if operation == "edits":
            result = await async_client.post(
                "/v1/images/edits",
                data={"model": MODEL, "prompt": "edit", "stream": str(stream).lower()},
                files={"image": ("test.png", b"png-test", "image/png")},
            )
            assert (
                requests[0]["input_references"][0]["image_url"]["url"]
                == "data:image/png;base64," + base64.b64encode(b"png-test").decode()
            )
        else:
            result = await async_client.post(
                "/v1/images/generations", json={"model": MODEL, "prompt": "draw", "stream": stream, "quality": "max"}
            )
        assert result.status_code == 200, result.text
        assert requests[0]["model"] == image_provider.data[0].id
        assert requests[0]["provider"] == {"sort": "price", "only": ["openai"]}
        if stream:
            prefix = "image_edit" if operation == "edits" else "image_generation"
            assert f"event: {prefix}.partial_image" in result.text
            assert f"event: {prefix}.completed" in result.text
            assert '"cost": 0.012' in result.text
        else:
            assert result.json()["data"][0]["b64_json"] == IMAGE
            assert result.json()["usage"]["input_tokens"] == 10
        async with SessionLocal() as session:
            logs = list(await session.scalars(select(RequestLog).where(RequestLog.model_source_id == account_id)))
            assert len(logs) == 1
            assert logs[0].cost_usd == pytest.approx(0.012)
            assert logs[0].input_tokens == 10


@pytest.mark.parametrize(
    "extra",
    [
        {"quality": "unsupported"},
        {"mask": "bad"},
        {"partial_images": 2},
        {"response_format": "url"},
        {"n": 11},
        {"stream": True, "n": 2},
    ],
)
async def test_image_parameters_rejected_without_dispatch(async_client, image_provider, extra):
    async def upstream(request):
        pytest.fail("invalid request reached upstream")

    async with stub_source_upstreams() as start:
        await create_account(async_client, await start(upstream))
        result = await async_client.post("/v1/images/generations", json={"model": MODEL, "prompt": "draw", **extra})
        assert result.status_code == 400, result.text


@pytest.mark.parametrize("status", [400, 401, 402, 429, 503])
async def test_image_error_preserves_status_and_no_retry(async_client, image_provider, status):
    calls = []

    async def upstream(request):
        calls.append(1)
        return web.json_response(
            {"error": {"code": status, "message": "image-secret denied"}}, status=status, headers={"Retry-After": "30"}
        )

    async with stub_source_upstreams() as start:
        await create_account(async_client, await start(upstream))
        result = await async_client.post("/v1/images/generations", json={"model": MODEL, "prompt": "draw"})
        assert result.status_code == status, result.text
        assert result.json()["error"]["code"] == str(status)
        assert result.headers["Retry-After"] == "30"
        assert "image-secret" not in result.text
        assert calls == [1]


async def test_incomplete_stream_is_not_billed(async_client, image_provider):
    async def upstream(request):
        return web.Response(
            text=f'data: {{"type":"image_generation.partial_image","b64_json":"{IMAGE}"}}\n\ndata: [DONE]\n\n',
            content_type="text/event-stream",
        )

    async with stub_source_upstreams() as start:
        account_id = await create_account(async_client, await start(upstream))
        result = await async_client.post(
            "/v1/images/generations", json={"model": MODEL, "prompt": "draw", "stream": True}
        )
        assert "stream_incomplete" in result.text
        async with SessionLocal() as session:
            log = await session.scalar(select(RequestLog).where(RequestLog.model_source_id == account_id))
            assert log.status == "error"
            assert log.cost_usd is None


async def test_paused_and_scoped_image_accounts_do_not_fall_through(async_client, image_provider):
    async def upstream(request):
        pytest.fail("unavailable account reached upstream")

    async with stub_source_upstreams() as start:
        account_id = await create_account(async_client, await start(upstream))
        await _enable_api_key_auth(async_client)
        other = (
            await async_client.post("/api/openrouter-accounts", json={"name": "Other", "apiKey": "other-secret"})
        ).json()["id"]
        key = (
            await async_client.post("/api/api-keys/", json={"name": "Other source", "assignedSourceIds": [other]})
        ).json()
        result = await async_client.post(
            "/v1/images/generations",
            headers={"Authorization": f"Bearer {key['key']}"},
            json={"model": MODEL, "prompt": "draw"},
        )
        assert result.status_code in {403, 404}, result.text
        await async_client.patch(f"/api/openrouter-accounts/{account_id}", json={"isEnabled": False})
        key = (
            await async_client.post("/api/api-keys/", json={"name": "Paused", "assignedSourceIds": [account_id]})
        ).json()
        result = await async_client.post(
            "/v1/images/generations",
            headers={"Authorization": f"Bearer {key['key']}"},
            json={"model": MODEL, "prompt": "draw"},
        )
        assert result.status_code == 404, result.text


@pytest.mark.parametrize("reported_cost", [None, 0.012])
async def test_image_cost_limits_settle_or_reject_missing_cost(async_client, image_provider, reported_cost):
    async def upstream(request):
        usage = {"prompt_tokens": 10, "completion_tokens": 20}
        if reported_cost is not None:
            usage["cost"] = reported_cost
        return web.json_response({"created": 1, "data": [{"b64_json": IMAGE}], "usage": usage})

    async with stub_source_upstreams() as start:
        account_id = await create_account(async_client, await start(upstream))
        await _enable_api_key_auth(async_client)
        created = await async_client.post(
            "/api/api-keys/",
            json={
                "name": "Image billing",
                "assignedSourceIds": [account_id],
                "limits": [{"limitType": "cost_usd", "limitWindow": "weekly", "maxValue": 1_000_000}],
            },
        )
        assert created.status_code == 200, created.text
        key = created.json()
        result = await async_client.post(
            "/v1/images/generations",
            headers={"Authorization": f"Bearer {key['key']}"},
            json={"model": MODEL, "prompt": "draw"},
        )
        assert result.status_code == (200 if reported_cost is not None else 502), result.text
        async with SessionLocal() as session:
            reservations = list(
                await session.scalars(
                    select(ApiKeyUsageReservation).where(ApiKeyUsageReservation.api_key_id == key["id"])
                )
            )
            assert all(row.status != "reserved" for row in reservations)
            log = await session.scalar(select(RequestLog).where(RequestLog.model_source_id == account_id))
            assert log.cost_usd == reported_cost
        details = (await async_client.get("/api/api-keys/")).json()
        entry = next(item for item in details if item["id"] == key["id"])
        assert entry["limits"][0]["currentValue"] == (12000 if reported_cost is not None else 0)


@pytest.mark.parametrize("before_body", [False, True])
async def test_image_disconnect_closes_stream_and_releases_reservation(async_client, image_provider, before_body):
    async def upstream(request):
        response = web.StreamResponse(headers={"Content-Type": "text/event-stream"})
        await response.prepare(request)
        await response.write(f'data: {{"type":"image_generation.partial_image","b64_json":"{IMAGE}"}}\n\n'.encode())
        await asyncio.Event().wait()
        return response

    async with stub_source_upstreams() as start:
        account_id = await create_account(
            async_client, await start(upstream, handler_cancellation=True, shutdown_timeout=0.1)
        )
        await _enable_api_key_auth(async_client)
        key = (
            await async_client.post(
                "/api/api-keys/",
                json={
                    "name": "Disconnect",
                    "assignedSourceIds": [account_id],
                    "weeklyTokenLimit": 10000,
                },
            )
        ).json()
        client = _AsgiStream(
            app=async_client._transport.app,
            path="/v1/images/generations",
            headers={"Authorization": f"Bearer {key['key']}"},
            body=json.dumps({"model": MODEL, "prompt": "draw", "stream": True}).encode(),
            stall_response_start=before_body,
        )
        task = asyncio.create_task(client.run())
        try:
            if before_body:
                await client.wait_for_response_start()
            else:
                await client.wait_for_text("partial_image")
            client.disconnect()
            await asyncio.wait_for(task, 5)
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        async with SessionLocal() as session:
            log = await session.scalar(select(RequestLog).where(RequestLog.model_source_id == account_id))
            assert log.status == "error"
            assert log.error_code == "client_disconnected"
            reservations = list(
                await session.scalars(
                    select(ApiKeyUsageReservation).where(ApiKeyUsageReservation.api_key_id == key["id"])
                )
            )
            assert all(row.status != "reserved" for row in reservations)


async def test_image_does_not_dispatch_as_responses(async_client, image_provider):
    async def upstream(request):
        pytest.fail("image-only model reached a conversation endpoint")

    async with stub_source_upstreams() as start:
        await create_account(async_client, await start(upstream))
        result = await async_client.post("/v1/responses", json={"model": MODEL, "input": "hi"})
        assert result.status_code == 400, result.text


async def test_missing_image_cost_stays_unknown(async_client, image_provider):
    async def upstream(request):
        return web.json_response(
            {"created": 1, "data": [{"b64_json": IMAGE}], "usage": {"prompt_tokens": 1, "completion_tokens": 2}}
        )

    async with stub_source_upstreams() as start:
        account_id = await create_account(async_client, await start(upstream))
        result = await async_client.post("/v1/images/generations", json={"model": MODEL, "prompt": "draw"})
        assert result.status_code == 200, result.text
        assert "cost" not in result.json()["usage"]
        async with SessionLocal() as session:
            log = await session.scalar(select(RequestLog).where(RequestLog.model_source_id == account_id))
            assert log.cost_usd is None


@pytest.mark.parametrize("failure", ["oversized", "malformed", "wrong_content_type", "redirect", "stream_error"])
async def test_image_transport_failures_are_bounded_and_terminal(async_client, image_provider, monkeypatch, failure):
    from app.modules.openrouter import images

    calls = []

    async def upstream(request):
        calls.append(1)
        if failure == "oversized":
            return web.Response(body=b"x" * 2000)
        if failure == "redirect":
            return web.Response(status=307, headers={"Location": "/must-not-follow"})
        if failure == "stream_error":
            return web.Response(
                text='data: {"type":"error","error":{"code":429,"message":"provider busy"}}\n\n',
                content_type="text/event-stream",
            )
        return web.Response(text="not an image response")

    async with stub_source_upstreams() as start:
        account_id = await create_account(async_client, await start(upstream))
        if failure == "oversized":
            monkeypatch.setattr(images, "MAX_IMAGE_RESPONSE_BYTES", 1000)
        result = await async_client.post(
            "/v1/images/generations",
            json={"model": MODEL, "prompt": "draw", "stream": failure in {"wrong_content_type", "stream_error"}},
        )
        assert result.status_code == (200 if failure == "stream_error" else 502), result.text
        if failure == "stream_error":
            assert '"code": "429"' in result.text
            assert "provider busy" in result.text
            assert "image_generation.completed" not in result.text
        assert calls == [1]
        async with SessionLocal() as session:
            logs = list(await session.scalars(select(RequestLog).where(RequestLog.model_source_id == account_id)))
            assert len(logs) == 1
            assert logs[0].status == "error"


async def test_image_refresh_retains_snapshot_on_endpoint_failure(async_client, image_provider, monkeypatch):
    from app.modules.openrouter.client import OpenRouterError

    async def upstream(request):
        return web.json_response({"created": 1, "data": [{"b64_json": IMAGE}], "usage": USAGE})

    async def failed(self, key, model):
        raise OpenRouterError("Image endpoints unavailable")

    async with stub_source_upstreams() as start:
        account_id = await create_account(async_client, await start(upstream))
        before = (await async_client.get("/api/openrouter-accounts")).json()["accounts"][0]["state"]["catalog"]
        monkeypatch.setattr(OpenRouterClient, "image_endpoints", failed)
        refreshed = await async_client.post(f"/api/openrouter-accounts/{account_id}/refresh")
        assert refreshed.status_code == 200
        assert refreshed.json()["state"]["catalog"] == before
        assert refreshed.json()["state"]["catalog_error"] == "Image endpoints unavailable"
