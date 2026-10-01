import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import update

from app.db.models import ClaudeAccount
from app.db.session import SessionLocal
from app.modules.claude.client import ClaudeClient
from app.modules.claude.metadata import MetadataHTTPError
from app.modules.claude.repository import ClaudeRepository
from app.modules.claude.schemas import AccountState, BootstrapResponse, CatalogModel, UsageSnapshot
from app.modules.claude.service import ClaudeService
from tests.integration import test_claude_accounts as account_fixtures
from tests.integration.test_claude_accounts import import_body

pytestmark = pytest.mark.integration
profile_stub = account_fixtures.profile_stub


def bootstrap(plan="claude_max", tier="default_claude_max_20x", *, account="access-secret", org="org-test"):
    return BootstrapResponse.model_validate(
        {
            "oauth_account": {
                "account_uuid": account,
                "organization_uuid": org,
                "organization_type": plan,
                "organization_rate_limit_tier": tier,
            }
        }
    )


@pytest.fixture
async def account(async_client, monkeypatch):
    monkeypatch.setattr(
        ClaudeClient, "catalog", AsyncMock(return_value=[CatalogModel(id="claude-test", display_name="Test")])
    )
    monkeypatch.setattr(ClaudeClient, "usage", AsyncMock(return_value=UsageSnapshot()))
    monkeypatch.setattr(ClaudeClient, "bootstrap", AsyncMock(return_value=bootstrap()))
    body = import_body()
    body["credentials"]["claudeAiOauth"]["subscriptionType"] = "pro"
    response = await async_client.post("/api/claude-accounts/import", json=body)
    assert response.status_code == 200, response.text
    assert response.json()["planType"] == "pro"
    assert "access-secret" not in response.text
    return response.json()["id"]


async def poll(source_id, *, force=True):
    async with SessionLocal() as session:
        return await ClaudeService(ClaudeRepository(session)).refresh(source_id, force=force)


async def test_import_and_discovery_public_response(async_client, account, monkeypatch):
    path = f"/api/claude-accounts/{account}/refresh"
    result = await async_client.post(path)
    assert result.status_code == 200, result.text
    body = result.json()
    assert body["planType"] == "max_20x"
    assert body["state"]["subscription"]["source"] == "bootstrap"
    assert body["state"]["subscription_updated_at"] is not None
    assert "access-secret" not in result.text and "org-test" not in result.text
    assert body["routingPolicy"] == "normal" and body["maxConcurrency"] is None
    listed = (await async_client.get("/api/claude-accounts")).json()["accounts"][0]
    assert listed["planType"] == "max_20x"
    monkeypatch.setattr(ClaudeClient, "bootstrap", AsyncMock(return_value=bootstrap("claude_free", None)))
    assert (await async_client.post(path)).json()["planType"] == "free"
    monkeypatch.setattr(ClaudeClient, "bootstrap", AsyncMock(return_value=bootstrap("future", "future")))
    assert (await async_client.post(path)).json()["planType"] == "unknown"


async def test_subscription_cooldown_retains_data_and_other_endpoints_continue(async_client, account, monkeypatch):
    original = await poll(account)
    failure = AsyncMock(side_effect=MetadataHTTPError("/api/claude_cli/bootstrap", 429, "600"))
    monkeypatch.setattr(ClaudeClient, "bootstrap", failure)
    for _ in range(2):
        result = await poll(account)
        assert result.plan_type == "max_20x"
        assert result.state.subscription == original.state.subscription
        assert result.state.subscription_updated_at == original.state.subscription_updated_at
        assert "429" in result.state.subscription_error
        assert result.credential_status == "ready" and result.is_enabled
    failure.assert_awaited_once()
    assert ClaudeClient.catalog.await_count == ClaudeClient.usage.await_count == 3
    async with SessionLocal() as session:
        row = await session.get(ClaudeAccount, account)
        assert row is not None
        assert row.retry_at is None and row.source.health_status == "unknown"
        state = AccountState.model_validate_json(row.state_json)
        state.metadata_refresh["subscription"].retry_at = datetime.now(UTC) - timedelta(seconds=1)
        row.state_json = state.model_dump_json()
        await session.commit()
    monkeypatch.setattr(ClaudeClient, "bootstrap", AsyncMock(return_value=bootstrap("claude_pro", None)))
    recovered = await poll(account, force=False)
    assert recovered.plan_type == "pro"
    assert recovered.state.subscription_error is None
    assert recovered.state.metadata_refresh["subscription"].retry_at is None


async def test_scheduled_discovery_for_existing_account_and_success_cadence(account):
    # Pre-feature persisted state has neither subscription fields nor a claim.
    import json

    async with SessionLocal() as session:
        row = await session.get(ClaudeAccount, account)
        legacy = json.loads(row.state_json)
        for field in ("subscription", "subscription_updated_at", "subscription_error"):
            legacy.pop(field)
        row.state_json = json.dumps(legacy)
        await session.commit()
    first = await poll(account, force=False)
    assert first.plan_type == "max_20x"
    await poll(account, force=False)
    ClaudeClient.bootstrap.assert_awaited_once()
    async with SessionLocal() as session:
        row = await session.get(ClaudeAccount, account)
        state = AccountState.model_validate_json(row.state_json)
        state.subscription_updated_at = datetime.now(UTC) - timedelta(hours=7)
        row.state_json = state.model_dump_json()
        await session.commit()
    await poll(account, force=False)
    assert ClaudeClient.bootstrap.await_count == 2


@pytest.mark.parametrize("identity", [{"account": "other-account"}, {"org": "other-org"}])
async def test_foreign_bootstrap_never_overwrites_plan(account, monkeypatch, identity):
    monkeypatch.setattr(ClaudeClient, "bootstrap", AsyncMock(return_value=bootstrap(**identity)))
    result = await poll(account)
    assert result.plan_type == "pro"
    assert result.state.subscription.source == "credential_file"
    assert "does not match" in result.state.subscription_error
    assert result.state.subscription_updated_at is None


async def test_reconnect_keeps_last_observation_and_schedules_new_discovery(async_client, account):
    original = await poll(account)
    body = import_body()
    body.pop("name")
    body["credentials"]["claudeAiOauth"]["refreshToken"] = "replacement-grant"
    reconnected = await async_client.post(f"/api/claude-accounts/{account}/reconnect", json=body)
    assert reconnected.status_code == 200, reconnected.text
    assert reconnected.json()["state"]["subscription"] == original.state.subscription.model_dump(mode="json")
    assert reconnected.json()["planType"] == "max_20x"
    assert reconnected.json()["state"]["subscription_updated_at"] is None
    await poll(account, force=False)
    assert ClaudeClient.bootstrap.await_count == 2


async def test_reconnect_with_explicit_subscription_updates_imported_hint(async_client, account):
    await poll(account)
    body = import_body()
    body.pop("name")
    body["credentials"]["claudeAiOauth"].update(
        refreshToken="new-grant", subscriptionType="max", rateLimitTier="default_claude_max_5x"
    )
    response = await async_client.post(f"/api/claude-accounts/{account}/reconnect", json=body)
    assert response.status_code == 200, response.text
    assert response.json()["planType"] == "max_5x"
    assert response.json()["state"]["subscription"]["source"] == "credential_file"
    assert response.json()["state"]["subscription_updated_at"] is None


async def test_rotating_expired_credentials_does_not_discard_subscription(account):
    from app.core.crypto import TokenEncryptor
    from app.modules.claude.auth import ClaudeAuth
    from app.modules.claude.credentials import decrypt_credentials, encrypt_credentials
    from tests.integration.test_claude_auth_recovery import rotated

    original = await poll(account)
    async with SessionLocal() as session:
        row = await session.get(ClaudeAccount, account)
        encryptor = TokenEncryptor()
        credentials = decrypt_credentials(row.credentials_encrypted, encryptor)
        credentials.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        row.credentials_encrypted = encrypt_credentials(credentials, encryptor)
        row.expires_at = credentials.expires_at.replace(tzinfo=None)
        await session.commit()
    client = ClaudeClient()
    client.refresh = AsyncMock(side_effect=rotated)
    async with SessionLocal() as session:
        repository = ClaudeRepository(session)
        snapshot = await ClaudeAuth(repository, client, TokenEncryptor()).snapshot(account)
        assert snapshot.generation == 2
        state = AccountState.model_validate_json((await repository.get(account)).state_json)
        assert state.subscription == original.state.subscription
        assert state.subscription_updated_at == original.state.subscription_updated_at


async def test_malformed_subscription_discovery_retains_last_observation(account, monkeypatch):
    from app.modules.claude.credentials import ClaudeError

    original = await poll(account)
    fetch = AsyncMock(side_effect=ClaudeError("Claude bootstrap returned invalid metadata"))
    monkeypatch.setattr(ClaudeClient, "bootstrap", fetch)
    result = await poll(account)
    assert result.plan_type == "max_20x"
    assert result.state.subscription == original.state.subscription
    assert result.state.subscription_updated_at == original.state.subscription_updated_at
    assert result.state.subscription_error == "Claude bootstrap returned invalid metadata"
    assert result.state.metadata_refresh["subscription"].retry_at > datetime.now(UTC)
    assert result.credential_status == "ready" and result.is_enabled
    await poll(account)
    fetch.assert_awaited_once()


@pytest.mark.parametrize("replace_generation", [False, True])
async def test_subscription_claim_deduplicates_and_fences_late_response(account, monkeypatch, replace_generation):
    entered, release = asyncio.Event(), asyncio.Event()

    async def delayed(*args):
        entered.set()
        await release.wait()
        return bootstrap()

    fetch = AsyncMock(side_effect=delayed)
    monkeypatch.setattr(ClaudeClient, "bootstrap", fetch)
    task = asyncio.create_task(poll(account))
    try:
        await asyncio.wait_for(entered.wait(), timeout=5)
        concurrent = await poll(account)
        assert concurrent.plan_type == "pro"
        fetch.assert_awaited_once()
        if replace_generation:
            async with SessionLocal() as session:
                await session.execute(
                    update(ClaudeAccount).where(ClaudeAccount.source_id == account).values(generation=2)
                )
                await session.commit()
        release.set()
        result = await task
        assert result.plan_type == ("pro" if replace_generation else "max_20x")
    finally:
        release.set()
        if not task.done():
            task.cancel()
        await asyncio.gather(task, return_exceptions=True)
