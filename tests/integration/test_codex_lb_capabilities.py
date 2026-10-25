from __future__ import annotations

import pytest

from app.core.config.settings_cache import get_settings_cache
from app.core.openai.model_registry import get_model_registry
from app.db.models import DashboardSettings
from app.db.session import SessionLocal
from app.modules.api_keys.repository import ApiKeysRepository
from app.modules.api_keys.service import ApiKeyCreateData, ApiKeysService
from app.modules.proxy.api import _is_codex_backend_catalog_model
from tests.integration import test_claude_provider_history as provider_fixtures

pytestmark = pytest.mark.integration
opus_pool = provider_fixtures.opus_pool

PATHS = ["/backend-api/codex/codex-lb/capabilities", "/v1/codex-lb/capabilities"]


def _native_slugs() -> list[str]:
    return sorted(
        slug
        for slug, model in get_model_registry().get_models_with_fallback().items()
        if _is_codex_backend_catalog_model(model)
    )


def _prediction_models(document: dict) -> list[str]:
    (capability,) = document["capabilities"]
    assert capability["id"] == "composer_predictions"
    return capability["models"]


async def _enable_api_key_auth() -> None:
    async with SessionLocal() as session:
        settings = await session.get(DashboardSettings, 1)
        assert settings is not None
        settings.api_key_auth_enabled = True
        await session.commit()
    await get_settings_cache().invalidate()


@pytest.mark.parametrize("path", PATHS)
async def test_capabilities_identify_codex_lb(async_client, path):
    response = await async_client.get(path)
    assert response.status_code == 200
    assert response.json() == {
        "object": "codex_lb.capabilities",
        "service": "codex-lb",
        "capabilities": [{"id": "composer_predictions", "models": _native_slugs()}],
    }


@pytest.mark.parametrize("path", PATHS)
async def test_predictions_exclude_routed_source_models(async_client, opus_pool, path):
    catalog = await async_client.get("/backend-api/codex/models", params={"client_version": "0.163.0"})
    assert catalog.status_code == 200, catalog.text
    catalog_slugs = {entry["slug"] for entry in catalog.json()["models"]}
    source_slugs = catalog_slugs - set(_native_slugs())
    assert source_slugs, "the Claude pool should add a routed model to the catalog"

    response = await async_client.get(path)
    assert response.status_code == 200
    models = _prediction_models(response.json())
    assert models == _native_slugs()
    assert not source_slugs & set(models)


@pytest.mark.parametrize("path", PATHS)
async def test_predictions_follow_the_key_model_allowlist(async_client, path):
    allowed = _native_slugs()[0]
    await get_settings_cache().get()
    await _enable_api_key_auth()
    async with SessionLocal() as session:
        created = await ApiKeysService(ApiKeysRepository(session)).create_key(
            ApiKeyCreateData(name="prediction-key", allowed_models=[allowed], expires_at=None)
        )

    response = await async_client.get(path, headers={"Authorization": f"Bearer {created.key}"})
    assert response.status_code == 200
    assert _prediction_models(response.json()) == [allowed]


@pytest.mark.parametrize("path", PATHS)
async def test_capabilities_require_the_proxy_api_key(async_client, path):
    await get_settings_cache().get()
    await _enable_api_key_auth()
    async with SessionLocal() as session:
        created = await ApiKeysService(ApiKeysRepository(session)).create_key(
            ApiKeyCreateData(name="capabilities-key", allowed_models=None, expires_at=None)
        )

    missing = await async_client.get(path)
    assert missing.status_code == 401
    assert missing.json()["error"]["code"] == "invalid_api_key"

    valid = await async_client.get(path, headers={"Authorization": f"Bearer {created.key}"})
    assert valid.status_code == 200
    assert valid.json()["service"] == "codex-lb"
