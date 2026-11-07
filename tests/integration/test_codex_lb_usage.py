from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.core.config.settings_cache import get_settings_cache
from app.core.crypto import TokenEncryptor
from app.core.openai.model_registry import get_model_registry
from app.core.utils.time import utcnow
from app.db.models import Account, AccountStatus, DashboardSettings, RequestLog
from app.db.session import SessionLocal
from app.modules.accounts.repository import AccountsRepository
from app.modules.api_keys.repository import ApiKeysRepository
from app.modules.api_keys.service import ApiKeyCreateData, ApiKeysService
from app.modules.usage.repository import UsageRepository
from tests.integration import test_claude_provider_history as provider_fixtures

pytestmark = pytest.mark.integration
opus_pool = provider_fixtures.opus_pool

PATHS = ["/backend-api/codex/codex-lb/usage", "/v1/codex-lb/usage"]


def _since(hours: float = 6) -> str:
    return (datetime.now(UTC) - timedelta(hours=hours)).isoformat()


async def _update_settings(**fields: object) -> None:
    await get_settings_cache().get()
    async with SessionLocal() as session:
        settings = await session.get(DashboardSettings, 1)
        assert settings is not None
        for name, value in fields.items():
            setattr(settings, name, value)
        await session.commit()
    await get_settings_cache().invalidate()


async def _create_key(name: str) -> tuple[str, str]:
    async with SessionLocal() as session:
        created = await ApiKeysService(ApiKeysRepository(session)).create_key(
            ApiKeyCreateData(name=name, allowed_models=None, expires_at=None)
        )
    return created.id, created.key


async def _seed_account(account_id: str, plan_type: str, *, weekly_used: float, resets_in: timedelta) -> None:
    encryptor = TokenEncryptor()
    async with SessionLocal() as session:
        await AccountsRepository(session).upsert(
            Account(
                id=account_id,
                chatgpt_account_id=None,
                email=account_id + "@example.com",
                plan_type=plan_type,
                access_token_encrypted=encryptor.encrypt("access"),
                refresh_token_encrypted=encryptor.encrypt("refresh"),
                id_token_encrypted=encryptor.encrypt("id"),
                last_refresh=utcnow(),
                status=AccountStatus.ACTIVE,
                deactivation_reason=None,
            )
        )
        await UsageRepository(session).add_entry(
            account_id,
            weekly_used,
            window="secondary",
            reset_at=int((datetime.now(UTC) + resets_in).timestamp()),
            window_minutes=10080,
        )


async def _seed_request(api_key_id: str, request_id: str, *, requested_at: datetime, cost_usd: float) -> None:
    async with SessionLocal() as session:
        session.add(
            RequestLog(
                account_id=None,
                request_id=request_id,
                archive_request_id="archive-" + request_id,
                model="gpt-6-sol",
                requested_at=requested_at,
                status="success",
                input_tokens=100,
                output_tokens=10,
                cost_usd=cost_usd,
                api_key_id=api_key_id,
            )
        )
        await session.commit()


@pytest.mark.parametrize("path", PATHS)
async def test_usage_reports_each_pool_with_its_models(async_client, opus_pool, path):
    await _seed_account("pro-spent", "pro", weekly_used=100, resets_in=timedelta(hours=9))
    await _seed_account("pro", "pro", weekly_used=20, resets_in=timedelta(days=5))

    response = await async_client.get(path, params={"since": _since()})

    assert response.status_code == 200, response.text
    document = response.json()
    assert document["object"] == "codex_lb.usage"
    assert document["today"] is None
    chatgpt, claude = document["pools"]
    assert chatgpt["id"] == "chatgpt"
    assert chatgpt["accounts"] == {"total": 2, "ready": 1}
    (weekly,) = chatgpt["windows"]
    assert (weekly["id"], weekly["window_seconds"], weekly["left_percent"]) == ("weekly", 604800, 40.0)
    assert set(chatgpt["models"]) <= set(get_model_registry().get_models_with_fallback())
    assert claude["kind"] == "claude"
    assert claude["models"] == ["anthropic/claude-opus-5-5"]


async def test_usage_counts_the_key_requests_since_the_client_day_began(async_client):
    await _update_settings(api_key_auth_enabled=True)
    key_id, key = await _create_key("usage-key")
    other_id, _ = await _create_key("other-key")
    now = utcnow()
    await _seed_request(key_id, "today-1", requested_at=now - timedelta(hours=1), cost_usd=1.25)
    await _seed_request(key_id, "today-2", requested_at=now - timedelta(hours=2), cost_usd=0.5)
    await _seed_request(key_id, "yesterday", requested_at=now - timedelta(hours=8), cost_usd=9.0)
    await _seed_request(other_id, "other", requested_at=now - timedelta(hours=1), cost_usd=4.0)

    since = _since(hours=6)
    response = await async_client.get(PATHS[0], params={"since": since}, headers={"Authorization": "Bearer " + key})

    assert response.status_code == 200, response.text
    today = response.json()["today"]
    assert (today["requests"], today["cost_usd"]) == (2, 1.75)
    assert datetime.fromisoformat(today["since"]) == datetime.fromisoformat(since)


async def test_usage_rejects_a_day_start_outside_the_last_day(async_client):
    response = await async_client.get(PATHS[0], params={"since": _since(hours=30)})

    assert response.status_code == 400


async def test_usage_requires_a_time_zone_on_the_day_start(async_client):
    response = await async_client.get(PATHS[0], params={"since": "2026-11-07T00:00:00"})

    assert response.status_code == 400


async def test_usage_requires_the_proxy_api_key(async_client):
    await _update_settings(api_key_auth_enabled=True)

    response = await async_client.get(PATHS[0], params={"since": _since()})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_api_key"


async def test_hidden_upstream_quota_withholds_usage(async_client):
    await _update_settings(api_key_auth_enabled=True, hide_upstream_quota_from_api_keys=True)
    _, key = await _create_key("hidden-key")
    headers = {"Authorization": "Bearer " + key}

    usage = await async_client.get(PATHS[0], params={"since": _since()}, headers=headers)
    capabilities = await async_client.get("/backend-api/codex/codex-lb/capabilities", headers=headers)

    assert usage.status_code == 403
    assert [capability["id"] for capability in capabilities.json()["capabilities"]] == ["composer_predictions"]
