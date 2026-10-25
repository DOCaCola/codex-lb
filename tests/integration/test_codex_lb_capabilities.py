from __future__ import annotations

import pytest

from app.core.config.settings_cache import get_settings_cache
from app.db.models import DashboardSettings
from app.db.session import SessionLocal
from app.modules.api_keys.repository import ApiKeysRepository
from app.modules.api_keys.service import ApiKeyCreateData, ApiKeysService

pytestmark = pytest.mark.integration

PATHS = ["/backend-api/codex/codex-lb/capabilities", "/v1/codex-lb/capabilities"]


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
        "capabilities": ["composer_predictions"],
    }


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
