from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from app.core.crypto import TokenEncryptor
from app.db.models import ClaudeAccount
from app.db.session import SessionLocal
from app.modules.claude.auth import ClaudeAuth
from app.modules.claude.client import ClaudeClient, TokenOutcomeUncertain, TokenRejected
from app.modules.claude.credentials import ClaudeError, decrypt_credentials
from app.modules.claude.repository import ClaudeRepository
from app.modules.claude.schemas import CatalogModel, Credentials, UsageSnapshot

pytestmark = pytest.mark.integration


def import_body(*, expired=False, refresh="refresh-secret"):
    return {
        "name": "Claude test",
        "acknowledgeExclusiveRefresh": True,
        "credentials": {
            "claudeAiOauth": {
                "accessToken": "access-secret",
                "refreshToken": refresh,
                "expiresAt": int((datetime.now(UTC) + timedelta(hours=-1 if expired else 1)).timestamp() * 1000),
                "scopes": ["user:inference", "user:profile"],
            }
        },
    }


async def test_import_encryption_duplicate_and_pause(async_client):
    response = await async_client.post("/api/claude-accounts/import", json=import_body())
    assert response.status_code == 200, response.text
    assert "secret" not in response.text
    source_id = response.json()["id"]
    async with SessionLocal() as session:
        row = await session.get(ClaudeAccount, source_id)
        assert row.source.api_key_encrypted is None
        assert b"secret" not in row.credentials_encrypted
        assert (
            decrypt_credentials(row.credentials_encrypted, TokenEncryptor()).access_token.get_secret_value()
            == "access-secret"
        )
    duplicate = await async_client.post("/api/claude-accounts/import", json=import_body())
    assert duplicate.status_code == 400
    paused = await async_client.patch(f"/api/claude-accounts/{source_id}", json={"isEnabled": False})
    assert paused.json()["isEnabled"] is False


async def test_catalog_refresh_preserves_snapshot_on_failure(async_client, monkeypatch):
    monkeypatch.setattr(
        ClaudeClient, "catalog", AsyncMock(return_value=[CatalogModel(id="claude-test", display_name="Test")])
    )
    monkeypatch.setattr(ClaudeClient, "usage", AsyncMock(return_value=UsageSnapshot()))
    source_id = (await async_client.post("/api/claude-accounts/import", json=import_body())).json()["id"]
    response = await async_client.post(f"/api/claude-accounts/{source_id}/refresh")
    assert response.status_code == 200, response.text
    assert response.json()["state"]["catalog"][0]["id"] == "claude-test"
    monkeypatch.setattr(ClaudeClient, "catalog", AsyncMock(side_effect=ClaudeError("Discovery unavailable")))
    response = await async_client.post(f"/api/claude-accounts/{source_id}/refresh")
    assert response.json()["state"]["catalog"][0]["id"] == "claude-test"
    assert response.json()["state"]["catalog_error"] == "Discovery unavailable"


@pytest.mark.parametrize(
    "failure,status",
    [
        (TokenRejected(400, terminal=True), "reauth_required"),
        (TokenRejected(503, terminal=False), "ready"),
        (TokenOutcomeUncertain("uncertain"), "uncertain"),
    ],
)
async def test_refresh_failure_survives_restart(async_client, failure, status):
    source_id = (await async_client.post("/api/claude-accounts/import", json=import_body(expired=True))).json()["id"]
    client = ClaudeClient()
    client.refresh = AsyncMock(side_effect=failure)
    async with SessionLocal() as session:
        auth = ClaudeAuth(ClaudeRepository(session), client, TokenEncryptor())
        with pytest.raises(ClaudeError):
            await auth.credentials(source_id)
    async with SessionLocal() as session:
        row = await session.get(ClaudeAccount, source_id)
        assert row.credential_status == status
        assert (row.refresh_intent is not None) == (status == "uncertain")
        with pytest.raises(ClaudeError):
            await ClaudeAuth(ClaudeRepository(session), client, TokenEncryptor()).credentials(source_id)
    assert client.refresh.await_count == 1


async def test_oauth_flow_is_single_use(async_client, monkeypatch):
    monkeypatch.setattr(ClaudeClient, "exchange", AsyncMock(side_effect=TokenOutcomeUncertain("uncertain")))
    started = await async_client.post(
        "/api/claude-accounts/oauth/start",
        json={
            "name": "OAuth",
            "acknowledgeExclusiveRefresh": True,
        },
    )
    assert started.status_code == 200, started.text
    body = {"state": started.json()["state"], "code": "test-code"}
    first = await async_client.post("/api/claude-accounts/oauth/complete", json=body)
    second = await async_client.post("/api/claude-accounts/oauth/complete", json=body)
    assert first.status_code == second.status_code == 400
    assert "already been used" in second.text
    assert ClaudeClient.exchange.await_count == 1


async def test_refresh_owned_across_workers_and_rotation_survives_restart(async_client):
    import asyncio

    source_id = (await async_client.post("/api/claude-accounts/import", json=import_body(expired=True))).json()["id"]
    entered, release = asyncio.Event(), asyncio.Event()
    rotated = Credentials(
        access_token="rotated-access",
        refresh_token="rotated-refresh",
        expires_at=datetime.now(UTC) + timedelta(hours=1),
        scopes=["user:inference"],
    )

    async def refresh(_credentials):
        entered.set()
        await release.wait()
        return rotated

    provider = ClaudeClient()
    provider.refresh = AsyncMock(side_effect=refresh)

    async def worker():
        async with SessionLocal() as session:
            return await ClaudeAuth(ClaudeRepository(session), provider, TokenEncryptor()).credentials(source_id)

    owner = asyncio.create_task(worker())
    try:
        await asyncio.wait_for(entered.wait(), timeout=5)
        with pytest.raises(ClaudeError, match="progress"):
            await worker()
    finally:
        release.set()
        await owner
    assert await worker() == rotated
    assert provider.refresh.await_count == 1
    async with SessionLocal() as session:
        row = await session.get(ClaudeAccount, source_id)
        assert row.generation == 2
        assert row.refresh_intent is None


async def test_definitive_refresh_rejection_can_recover_after_backoff(async_client):
    from sqlalchemy import update

    source_id = (await async_client.post("/api/claude-accounts/import", json=import_body(expired=True))).json()["id"]
    provider = ClaudeClient()
    rotated = Credentials(
        access_token="new-access",
        refresh_token="new-refresh",
        expires_at=datetime.now(UTC) + timedelta(hours=1),
        scopes=["user:inference"],
    )
    provider.refresh = AsyncMock(side_effect=[TokenRejected(503, terminal=False), rotated])
    async with SessionLocal() as session:
        with pytest.raises(TokenRejected):
            await ClaudeAuth(ClaudeRepository(session), provider, TokenEncryptor()).credentials(source_id)
    async with SessionLocal() as session:
        await session.execute(
            update(ClaudeAccount)
            .where(ClaudeAccount.source_id == source_id)
            .values(retry_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(seconds=1))
        )
        await session.commit()
        assert await ClaudeAuth(ClaudeRepository(session), provider, TokenEncryptor()).credentials(source_id) == rotated
    assert provider.refresh.await_count == 2


async def test_import_validation_does_not_echo_credentials(async_client):
    body = import_body()
    body["credentials"]["claudeAiOauth"]["expiresAt"] = 1
    response = await async_client.post("/api/claude-accounts/import", json=body)
    assert response.status_code in (400, 422)
    assert "access-secret" not in response.text
    assert "refresh-secret" not in response.text


async def test_expired_oauth_flow_never_exchanges(async_client, monkeypatch):
    from sqlalchemy import update

    from app.db.models import ClaudeOAuthFlow

    exchange = AsyncMock()
    monkeypatch.setattr(ClaudeClient, "exchange", exchange)
    started = await async_client.post(
        "/api/claude-accounts/oauth/start", json={"name": "OAuth", "acknowledgeExclusiveRefresh": True}
    )
    async with SessionLocal() as session:
        await session.execute(
            update(ClaudeOAuthFlow).values(expires_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(seconds=1))
        )
        await session.commit()
    response = await async_client.post(
        "/api/claude-accounts/oauth/complete", json={"state": started.json()["state"], "code": "secret-code"}
    )
    assert response.status_code == 400
    exchange.assert_not_awaited()
