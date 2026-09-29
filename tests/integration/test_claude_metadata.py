import asyncio
from datetime import UTC, datetime, timedelta
from typing import cast
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import update

from app.db.models import ClaudeAccount
from app.db.session import SessionLocal
from app.modules.claude import service as service_module
from app.modules.claude.auth import ClaudeAuth
from app.modules.claude.client import ClaudeClient
from app.modules.claude.metadata import MetadataHTTPError
from app.modules.claude.repository import ClaudeRepository
from app.modules.claude.schemas import CatalogModel, QuotaWindow, UsageSnapshot
from app.modules.claude.service import ClaudeService
from tests.integration.test_claude_accounts import import_body, install_profile_stub

pytestmark = pytest.mark.integration


@pytest.fixture
async def account(async_client, monkeypatch):
    install_profile_stub(monkeypatch)
    monkeypatch.setattr(
        ClaudeClient,
        "catalog",
        AsyncMock(
            return_value=[
                CatalogModel(id="claude-test", display_name="Test"),
            ]
        ),
    )
    monkeypatch.setattr(
        ClaudeClient,
        "usage",
        AsyncMock(
            return_value=UsageSnapshot(
                five_hour=QuotaWindow(utilization=25),
            )
        ),
    )
    response = await async_client.post("/api/claude-accounts/import", json=import_body())
    assert response.status_code == 200, response.text
    return response.json()["id"]


async def poll(source_id, **kwargs):
    async with SessionLocal() as session:
        return await ClaudeService(ClaudeRepository(session)).refresh(source_id, **kwargs)


async def mutate(source_id, callback):
    async with SessionLocal() as session:
        repo = ClaudeRepository(session)
        row = await repo.get(source_id)
        assert row is not None
        await repo.mutate_state(source_id, row.generation, callback)
        await session.commit()


@pytest.mark.parametrize("endpoint", ["usage", "catalog"])
async def test_route_cooldown_persists_keeps_readings_and_other_endpoint(
    async_client,
    account,
    monkeypatch,
    endpoint,
):
    path = f"/api/claude-accounts/{account}/refresh"
    original = (await async_client.post(path)).json()
    failure = AsyncMock(
        side_effect=MetadataHTTPError(
            "/api/oauth/usage" if endpoint == "usage" else "/v1/models",
            429,
            "600",
        )
    )
    monkeypatch.setattr(ClaudeClient, endpoint, failure)
    failed = await async_client.post(path)
    assert failed.status_code == 200, failed.text
    state = failed.json()["state"]
    assert state[endpoint] == original["state"][endpoint]
    assert state[f"{endpoint}_updated_at"] == original["state"][f"{endpoint}_updated_at"]
    assert "429" in state[f"{endpoint}_error"]
    assert failed.json()["isEnabled"] and failed.json()["credentialStatus"] == "ready"
    if endpoint == "usage":
        assert failed.json()["quota"]["windows"][0]["freshness"] == "stale"
    for _ in range(2):
        response = await async_client.post(path)
        assert response.status_code == 200
    assert failure.await_count == 1
    other = ClaudeClient.catalog if endpoint == "usage" else ClaudeClient.usage
    assert cast(AsyncMock, other).await_count == 4
    async with SessionLocal() as session:
        row = await session.get(ClaudeAccount, account)
        assert row is not None
        assert row.retry_at is None and row.refresh_intent is None
        assert row.source.health_status == "unknown"
    # Fresh services and scheduled calls honor the same persisted deadline.
    monkeypatch.setattr(ClaudeAuth, "snapshot", AsyncMock(side_effect=AssertionError("not due")))
    await poll(account, force=False)
    assert failure.await_count == 1


async def test_retry_expiry_success_clears_error_and_returns_fresh_reading(async_client, account, monkeypatch):
    failure = AsyncMock(side_effect=MetadataHTTPError("/api/oauth/usage", 429, None))
    monkeypatch.setattr(ClaudeClient, "usage", failure)
    await poll(account, catalog=False)
    before = datetime.now(UTC)

    def expire(state):
        assert state.metadata_refresh["usage"].retry_at > before + timedelta(seconds=170)
        state.metadata_refresh["usage"].retry_at = before - timedelta(seconds=1)
        return state

    await mutate(account, expire)
    monkeypatch.setattr(
        ClaudeClient,
        "usage",
        AsyncMock(
            return_value=UsageSnapshot(
                five_hour=QuotaWindow(utilization=30),
            )
        ),
    )
    recovered = await poll(account, catalog=False, force=False)
    assert recovered.state.usage_error is None
    assert recovered.state.metadata_refresh["usage"].retry_at is None
    assert recovered.quota.windows[0].freshness == "fresh"
    assert recovered.quota.windows[0].utilization == 30


async def test_scheduled_cache_does_not_refresh_auth_or_metadata(account, monkeypatch):
    await poll(account)
    monkeypatch.setattr(ClaudeAuth, "snapshot", AsyncMock(side_effect=AssertionError("not due")))
    await poll(account, force=False)
    assert cast(AsyncMock, ClaudeClient.usage).await_count == cast(AsyncMock, ClaudeClient.catalog).await_count == 1


@pytest.mark.parametrize("endpoint", ["usage", "catalog"])
async def test_failed_endpoint_retries_after_deadline_despite_recent_success(account, monkeypatch, endpoint):
    await poll(account)
    success = getattr(ClaudeClient, endpoint)
    failure = AsyncMock(side_effect=MetadataHTTPError(endpoint, 429, "600"))
    monkeypatch.setattr(ClaudeClient, endpoint, failure)
    await poll(account)

    def expire(state):
        state.metadata_refresh[endpoint].retry_at = datetime.now(UTC) - timedelta(seconds=1)
        return state

    await mutate(account, expire)
    monkeypatch.setattr(ClaudeClient, endpoint, success)
    result = await poll(account, force=False)
    assert cast(AsyncMock, success).await_count == 2
    assert result.state.metadata_refresh[endpoint].retry_at is None


async def test_concurrent_endpoint_refreshes_coalesce_across_workers(account, monkeypatch):
    entered = asyncio.Event()
    release = asyncio.Event()

    async def catalog(*args):
        entered.set()
        await release.wait()
        return []

    monkeypatch.setattr(ClaudeClient, "catalog", AsyncMock(side_effect=catalog))
    first = asyncio.create_task(poll(account))
    try:
        await asyncio.wait_for(entered.wait(), 5)
        # Second caller skips busy catalog and completes usage independently.
        await poll(account)
        release.set()
        await first
    finally:
        release.set()
        await asyncio.gather(first, return_exceptions=True)
    assert cast(AsyncMock, ClaudeClient.catalog).await_count == 1
    assert cast(AsyncMock, ClaudeClient.usage).await_count == 1


@pytest.mark.parametrize("replacement", ["generation", "claim", "expired"])
async def test_late_completion_cannot_overwrite_new_owner(account, monkeypatch, replacement):
    entered = asyncio.Event()
    release = asyncio.Event()

    async def usage(*args):
        entered.set()
        await release.wait()
        return UsageSnapshot(five_hour=QuotaWindow(utilization=99))

    monkeypatch.setattr(ClaudeClient, "usage", AsyncMock(side_effect=usage))
    task = asyncio.create_task(poll(account, catalog=False))
    try:
        await asyncio.wait_for(entered.wait(), 5)
        if replacement == "generation":
            async with SessionLocal() as session:
                await session.execute(
                    update(ClaudeAccount)
                    .where(ClaudeAccount.source_id == account)
                    .values(
                        generation=ClaudeAccount.generation + 1,
                    )
                )
                await session.commit()
        else:

            def change(state):
                refresh = state.metadata_refresh["usage"]
                if replacement == "claim":
                    refresh.operation_id = "new-owner"
                else:
                    refresh.lease_until = datetime.now(UTC) - timedelta(seconds=1)
                return state

            await mutate(account, change)
        release.set()
        result = await task
        assert result.state.usage is None
    finally:
        release.set()
        await asyncio.gather(task, return_exceptions=True)


async def test_cancellation_lease_blocks_then_expires(account, monkeypatch):
    entered = asyncio.Event()

    async def usage(*args):
        entered.set()
        await asyncio.Event().wait()

    monkeypatch.setattr(ClaudeClient, "usage", AsyncMock(side_effect=usage))
    task = asyncio.create_task(poll(account, catalog=False))
    try:
        await asyncio.wait_for(entered.wait(), 5)
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
    await poll(account, catalog=False)
    assert cast(AsyncMock, ClaudeClient.usage).await_count == 1

    def expire(state):
        state.metadata_refresh["usage"].lease_until = datetime.now(UTC) - timedelta(seconds=1)
        return state

    await mutate(account, expire)
    monkeypatch.setattr(ClaudeClient, "usage", AsyncMock(return_value=UsageSnapshot()))
    result = await poll(account, catalog=False)
    assert result.state.usage is not None
    assert result.state.metadata_refresh["usage"].operation_id is None


async def test_logical_catalog_timeout_does_not_prevent_usage(account, monkeypatch):
    async def catalog(*args):
        await asyncio.Event().wait()

    monkeypatch.setattr(service_module, "FETCH_TIMEOUT_SECONDS", 0.01)
    monkeypatch.setattr(ClaudeClient, "catalog", AsyncMock(side_effect=catalog))
    result = await poll(account)
    assert result.state.catalog_error == "Claude catalog metadata timed out"
    assert result.state.metadata_refresh["catalog"].retry_at is not None
    assert result.state.usage is not None
