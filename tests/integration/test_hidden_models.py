from __future__ import annotations

import json
from collections.abc import AsyncIterator
from dataclasses import replace

import pytest
from aiohttp import web

from app.core.openai.model_registry import UpstreamModel, get_model_registry
from tests.integration.model_source_helpers import _create_model_source as _create_routed_source
from tests.integration.model_source_helpers import stub_source_upstreams
from tests.integration.test_settings_audit_changed_fields import _wait_for_settings_changed_audit_log
from tests.integration.test_v1_models import _create_model_source, _make_upstream_model

pytestmark = pytest.mark.integration


@pytest.fixture
async def source_upstream() -> AsyncIterator:
    async with stub_source_upstreams() as start:
        yield start


async def _hide(async_client, slug: str) -> dict:
    response = await async_client.put(f"/api/settings/hidden-models/{slug}")
    assert response.status_code == 200, response.text
    return response.json()


async def _codex_entries(async_client, headers: dict[str, str] | None = None) -> tuple[dict[str, dict], set[str]]:
    response = await async_client.get("/backend-api/codex/models", headers=headers or {})
    assert response.status_code == 200, response.text
    body = response.json()
    return {entry["slug"]: entry for entry in body["models"]}, {item["id"] for item in body["data"]}


@pytest.mark.asyncio
async def test_hidden_native_model_keeps_its_codex_metadata_and_leaves_model_lists(async_client):
    models = [_make_upstream_model("gpt-old"), _make_upstream_model("gpt-new")]
    await get_model_registry().update({"pro": models})
    listed_entries, _ = await _codex_entries(async_client)

    await _hide(async_client, "gpt-old")

    entries, data = await _codex_entries(async_client)
    assert entries["gpt-old"]["visibility"] == "hide"
    assert {**entries["gpt-old"], "visibility": "list"} == listed_entries["gpt-old"]
    assert entries["gpt-new"]["visibility"] == "list"
    assert "gpt-old" not in data
    v1 = await async_client.get("/v1/models")
    assert {item["id"] for item in v1.json()["data"]} >= {"gpt-new"}
    assert "gpt-old" not in {item["id"] for item in v1.json()["data"]}
    codex_v1 = await async_client.get("/v1/models", params={"client_version": "0.160.0"})
    assert {entry["slug"]: entry["visibility"] for entry in codex_v1.json()["models"]}["gpt-old"] == "hide"


@pytest.mark.asyncio
async def test_hidden_source_model_leaves_the_openai_and_claude_code_lists(async_client):
    await get_model_registry().update({"pro": [_make_upstream_model("gpt-new")]})
    await _create_model_source(async_client, name="hidden-src", model="external-old", supports_responses=True)
    await _create_model_source(async_client, name="listed-src", model="external-new", supports_responses=True)

    await _hide(async_client, "external-old")

    entries, data = await _codex_entries(async_client)
    assert entries["external-old"]["visibility"] == "hide"
    assert entries["external-new"]["visibility"] == "list"
    assert "external-old" not in data
    openai_ids = {item["id"] for item in (await async_client.get("/v1/models")).json()["data"]}
    assert "external-new" in openai_ids
    assert "external-old" not in openai_ids
    anthropic = await async_client.get(
        "/v1/models", params={"limit": 1000}, headers={"anthropic-version": "2023-06-01"}
    )
    anthropic_ids = {entry["id"] for entry in anthropic.json()["data"]}
    assert "clb-claude-external-new" in anthropic_ids
    assert not any("external-old" in model_id for model_id in anthropic_ids)


@pytest.mark.asyncio
async def test_api_key_visibility_allowlist_does_not_list_a_hidden_model(async_client):
    models = [_make_upstream_model("gpt-old"), _make_upstream_model("gpt-new")]
    await get_model_registry().update({"pro": models})
    enabled = await async_client.put(
        "/api/settings",
        json={
            "stickyThreadsEnabled": False,
            "preferEarlierResetAccounts": False,
            "totpRequiredOnLogin": False,
            "apiKeyAuthEnabled": True,
        },
    )
    assert enabled.status_code == 200
    created = await async_client.post(
        "/api/api-keys/",
        json={"name": "visibility", "allowedModels": ["gpt-old", "gpt-new"], "applyToCodexModel": True},
    )
    assert created.status_code == 200, created.text
    headers = {"Authorization": f"Bearer {created.json()['key']}"}

    await _hide(async_client, "gpt-old")

    entries, _ = await _codex_entries(async_client, headers)
    assert entries["gpt-old"]["visibility"] == "hide"
    assert entries["gpt-new"]["visibility"] == "list"


@pytest.mark.asyncio
async def test_hiding_the_default_native_model_keeps_the_routed_prompt(async_client):
    def native(slug: str, priority: int, template: str) -> UpstreamModel:
        return replace(
            _make_upstream_model(
                slug,
                base_instructions=template,
                raw={
                    "shell_type": "shell_command",
                    "visibility": "list",
                    "availability_nux": None,
                    "model_messages": {"instructions_template": template},
                },
            ),
            priority=priority,
        )

    models = [
        native("gpt-default", 0, "You are Codex, an agent based on GPT-6. Default."),
        native("gpt-later", 1, "You are Codex, an agent based on GPT-6. Later."),
    ]
    await get_model_registry().update({"pro": models})
    await _create_model_source(async_client, name="routed-src", model="external-routed", supports_responses=True)

    await _hide(async_client, "gpt-default")

    entries, _ = await _codex_entries(async_client)
    assert entries["external-routed"]["base_instructions"] == "You are Codex, an agent. Default."


@pytest.mark.asyncio
async def test_hidden_source_model_is_still_routed(async_client, source_upstream):
    async def complete(request: web.Request) -> web.Response:
        body = await request.json()
        return web.json_response(
            {
                "id": "chatcmpl-hidden",
                "object": "chat.completion",
                "created": 1,
                "model": body["model"],
                "choices": [{"index": 0, "message": {"role": "assistant", "content": "ok"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 3, "completion_tokens": 1, "total_tokens": 4},
            }
        )

    base_url = await source_upstream(complete)
    await _create_routed_source(async_client, name="hidden-routed", model="external-hidden", base_url=base_url)
    await _hide(async_client, "external-hidden")

    response = await async_client.post(
        "/v1/chat/completions",
        json={"model": "external-hidden", "messages": [{"role": "user", "content": "hi"}]},
    )

    assert response.status_code == 200, response.text
    assert response.json()["choices"][0]["message"]["content"] == "ok"


@pytest.mark.asyncio
async def test_hidden_models_settings_api(async_client):
    await get_model_registry().update({"pro": [_make_upstream_model("gpt-old")]})

    def listed(body: dict) -> bool:
        return next(model["listed"] for model in body["models"] if model["slug"] == "gpt-old")

    initial = await async_client.get("/api/settings/model-context-window-overrides")
    assert listed(initial.json()) is True

    assert listed(await _hide(async_client, "gpt-old")) is False
    # Hiding again is a no-op.
    assert listed(await _hide(async_client, "gpt-old")) is False
    audit = await _wait_for_settings_changed_audit_log()
    assert audit.details is not None
    assert json.loads(audit.details) == {"changed_fields": ["hidden_models"], "slug": "gpt-old"}

    unknown = await async_client.put("/api/settings/hidden-models/unknown-model")
    assert unknown.status_code == 400
    assert unknown.json()["error"]["code"] == "model_not_in_catalogue"

    shown = await async_client.delete("/api/settings/hidden-models/gpt-old")
    assert shown.status_code == 200
    assert listed(shown.json()) is True
    entries, _ = await _codex_entries(async_client)
    assert entries["gpt-old"]["visibility"] == "list"

    missing = await async_client.delete("/api/settings/hidden-models/gpt-old")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "hidden_model_not_found"


@pytest.mark.asyncio
async def test_hidden_model_stays_hidden_after_leaving_the_catalogue(async_client):
    registry = get_model_registry()
    await registry.update({"pro": [_make_upstream_model("gpt-old"), _make_upstream_model("gpt-new")]})
    await _hide(async_client, "gpt-old")

    await registry.update({"pro": [_make_upstream_model("gpt-new")]})
    await registry.update({"pro": [_make_upstream_model("gpt-old"), _make_upstream_model("gpt-new")]})

    entries, _ = await _codex_entries(async_client)
    assert entries["gpt-old"]["visibility"] == "hide"


@pytest.mark.asyncio
async def test_catalog_keeps_the_last_known_hidden_models_when_the_read_fails(async_client, monkeypatch):
    await get_model_registry().update({"pro": [_make_upstream_model("gpt-old")]})
    await _hide(async_client, "gpt-old")
    entries, _ = await _codex_entries(async_client)
    assert entries["gpt-old"]["visibility"] == "hide"

    from app.core.openai.hidden_models import get_hidden_models_cache
    from app.modules.settings import repository as settings_repository_module

    await get_hidden_models_cache().invalidate(propagate=False)

    class _UnreachableRepository:
        def __init__(self, session) -> None:
            self._session = session

        async def slugs(self) -> frozenset[str]:
            raise RuntimeError("database unreachable")

    monkeypatch.setattr(settings_repository_module, "HiddenModelsRepository", _UnreachableRepository)
    entries, _ = await _codex_entries(async_client)
    assert entries["gpt-old"]["visibility"] == "hide"
