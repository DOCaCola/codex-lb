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


async def test_all_mode_projects_only_valid_metadata_and_retains_selected_mode(async_client, monkeypatch):
    monkeypatch.setattr(
        ClaudeClient,
        "catalog",
        AsyncMock(
            return_value=[
                CatalogModel(id="claude-opus-5", display_name="Opus", max_input_tokens=1000000, max_tokens=128000),
                CatalogModel(id="unknown", display_name="Unknown"),
            ]
        ),
    )
    monkeypatch.setattr(ClaudeClient, "usage", AsyncMock(return_value=UsageSnapshot()))
    created = await async_client.post("/api/claude-accounts/import", json=import_body())
    assert created.status_code == 200, created.text
    source_id = created.json()["id"]
    assert created.json()["state"]["all_models"] is False
    await async_client.post(f"/api/claude-accounts/{source_id}/refresh")
    enabled = await async_client.patch(f"/api/claude-accounts/{source_id}", json={"allModels": True})
    assert enabled.status_code == 200, enabled.text
    assert enabled.json()["state"]["selections"] == []
    assert [model["model"] for model in enabled.json()["quota"]["models"]] == ["claude-opus-5"]
    visible = (await async_client.get("/backend-api/codex/models")).json()["models"]
    assert any(model["slug"] == "anthropic/claude-opus-5" for model in visible)
    assert not any(model["slug"] == "anthropic/unknown" for model in visible)
    selected = await async_client.patch(
        f"/api/claude-accounts/{source_id}", json={"selections": [{"model": "claude-opus-5"}]}
    )
    assert selected.status_code == 200
    await async_client.post(f"/api/claude-accounts/{source_id}/refresh")
    off = await async_client.patch(f"/api/claude-accounts/{source_id}", json={"allModels": False})
    assert off.json()["state"]["selections"] == [{"model": "claude-opus-5"}]


def install_profile_stub(monkeypatch):
    from app.modules.claude.schemas import AuthenticatedProfile, BootstrapResponse

    async def profile(_self, token, _version):
        return AuthenticatedProfile.model_validate({"account": {"uuid": token}, "organization": {"uuid": "org-test"}})

    monkeypatch.setattr(ClaudeClient, "profile", profile)

    async def bootstrap(_self, token, _version):
        return BootstrapResponse.model_validate(
            {"oauth_account": {"account_uuid": token, "organization_uuid": "org-test"}}
        )

    monkeypatch.setattr(ClaudeClient, "bootstrap", bootstrap)


@pytest.fixture(autouse=True)
def profile_stub(monkeypatch):
    install_profile_stub(monkeypatch)


def import_body(*, expired=False, refresh="refresh-secret"):
    return {
        "name": "Claude test",
        "acknowledgeExclusiveRefresh": True,
        "credentials": {
            "claudeAiOauth": {
                "accessToken": "access-secret" if refresh == "refresh-secret" else f"access-{refresh}",
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
        assert row is not None
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


async def test_rotated_grant_cannot_duplicate_authenticated_account(async_client):
    first = await async_client.post("/api/claude-accounts/import", json=import_body())
    assert first.status_code == 200
    body = import_body()
    body["credentials"]["claudeAiOauth"]["refreshToken"] = "other-grant"
    duplicate = await async_client.post("/api/claude-accounts/import", json=body)
    assert duplicate.status_code == 400
    assert len((await async_client.get("/api/claude-accounts")).json()["accounts"]) == 1


async def test_accounts_are_listed_by_name(async_client):
    for name in ("Zulu", "Alpha", "Mike"):
        body = import_body(refresh=name.lower())
        body["name"] = name
        assert (await async_client.post("/api/claude-accounts/import", json=body)).status_code == 200
    accounts = (await async_client.get("/api/claude-accounts")).json()["accounts"]
    assert [account["name"] for account in accounts] == ["Alpha", "Mike", "Zulu"]


async def test_reconnect_preserves_identity_and_invalidates_old_refresh_generation(async_client):
    source_id = (await async_client.post("/api/claude-accounts/import", json=import_body())).json()["id"]
    async with SessionLocal() as session:
        row = await session.get(ClaudeAccount, source_id)
        assert row is not None
        row.credential_status = "uncertain"
        row.refresh_intent = "old-intent"
        await session.commit()
    body = import_body()
    body.pop("name")
    body["credentials"]["claudeAiOauth"]["refreshToken"] = "new-grant"
    response = await async_client.post(f"/api/claude-accounts/{source_id}/reconnect", json=body)
    assert response.status_code == 200, response.text
    assert response.json()["credentialStatus"] == "ready"
    async with SessionLocal() as session:
        row = await session.get(ClaudeAccount, source_id)
        assert row is not None
        assert row.generation == 2 and row.refresh_intent is None
        assert not await ClaudeRepository(session).finish_refresh(source_id, 1, "old-intent", status="ready")
    body["credentials"]["claudeAiOauth"]["accessToken"] = "other-account"
    rejected = await async_client.post(f"/api/claude-accounts/{source_id}/reconnect", json=body)
    assert rejected.status_code == 400
    assert "same authenticated Claude account" in rejected.text


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


async def test_automatic_catalog_limits_and_rejected_override_api(async_client, monkeypatch):
    monkeypatch.setattr(
        ClaudeClient,
        "catalog",
        AsyncMock(
            return_value=[
                CatalogModel(id="claude-opus-5", display_name="Opus", max_input_tokens=1000000, max_tokens=128000),
                CatalogModel(id="claude-future", display_name="Future"),
            ]
        ),
    )
    monkeypatch.setattr(ClaudeClient, "usage", AsyncMock(return_value=UsageSnapshot()))
    source_id = (await async_client.post("/api/claude-accounts/import", json=import_body())).json()["id"]
    path = f"/api/claude-accounts/{source_id}"
    await async_client.post(path + "/refresh")
    bad = await async_client.patch(path, json={"selections": [{"model": "claude-opus-5", "contextWindow": 200000}]})
    assert bad.status_code == 422
    unknown = await async_client.patch(path, json={"selections": [{"model": "claude-future"}]})
    assert unknown.status_code == 400
    good = await async_client.patch(
        path, json={"selections": [{"model": "claude-opus-5"}], "routingPolicy": "preserve"}
    )
    assert good.status_code == 200, good.text
    assert good.json()["routingPolicy"] == "preserve"
    assert good.json()["state"]["selections"] == [{"model": "claude-opus-5"}]
    catalog = (await async_client.get("/backend-api/codex/models")).json()["models"]
    model = next(item for item in catalog if item["slug"] == "anthropic/claude-opus-5")
    assert model["context_window"] == 272000
    assert model["max_context_window"] == 1000000
    assert model["max_output_tokens"] == 128000
    assert model["auto_compact_token_limit"] == 244800
    assert model["effective_context_window_percent"] == 95
    generic = (await async_client.get("/v1/models")).json()["data"]
    generic_model = next(item for item in generic if item["id"] == "anthropic/claude-opus-5")
    assert generic_model["context_length"] == generic_model["metadata"]["input_context_window"] == 272000
    assert generic_model["max_output_tokens"] == 128000
    assert good.json()["state"]["catalog"][0]["max_input_tokens"] == 1000000
    assert (await async_client.patch(path, json={"routingPolicy": "invalid"})).status_code == 422


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
        assert row is not None
        assert row.credential_status == status
        assert (row.refresh_intent is not None) == (status == "uncertain")
        with pytest.raises(ClaudeError):
            await ClaudeAuth(ClaudeRepository(session), client, TokenEncryptor()).credentials(source_id)
    assert client.refresh.await_count == 1


async def test_oauth_flow_is_single_use(async_client, monkeypatch):
    exchange = AsyncMock(side_effect=TokenOutcomeUncertain("uncertain"))
    monkeypatch.setattr(ClaudeClient, "exchange", exchange)
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
    assert exchange.await_count == 1


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
        assert row is not None
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


async def test_selected_catalog_and_quota_api_preserve_missing_entitlement(async_client, monkeypatch):
    from app.modules.claude.schemas import QuotaWindow

    catalog = AsyncMock(return_value=[CatalogModel(id="claude-opus-5", display_name="Opus")])
    monkeypatch.setattr(ClaudeClient, "catalog", catalog)
    monkeypatch.setattr(
        ClaudeClient,
        "usage",
        AsyncMock(
            return_value=UsageSnapshot(
                seven_day_opus=QuotaWindow(utilization=100, resets_at=datetime.now(UTC) + timedelta(hours=2)),
            )
        ),
    )
    source_id = (await async_client.post("/api/claude-accounts/import", json=import_body())).json()["id"]
    await async_client.post(f"/api/claude-accounts/{source_id}/refresh")
    response = await async_client.patch(
        f"/api/claude-accounts/{source_id}", json={"selections": [{"model": "claude-opus-5"}]}
    )
    assert response.status_code == 200, response.text
    assert response.json()["quota"]["models"][0]["blockingWindows"] == ["seven_day_opus"]
    invalid = await async_client.patch(
        f"/api/claude-accounts/{source_id}", json={"selections": [{"model": "invented"}]}
    )
    assert invalid.status_code == 400
    catalog.return_value = [CatalogModel(id="claude-sonnet-5", display_name="Sonnet")]
    response = await async_client.post(f"/api/claude-accounts/{source_id}/refresh")
    assert response.json()["state"]["selections"][0]["model"] == "claude-opus-5"
    async with SessionLocal() as session:
        from app.modules.model_sources.repository import ModelSourcesRepository

        source = await ModelSourcesRepository(session).get_by_id(source_id)
        assert source is not None
        assert [(model.model, model.is_enabled) for model in source.models] == [("anthropic/claude-opus-5", False)]
