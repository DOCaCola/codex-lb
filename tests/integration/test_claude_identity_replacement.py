from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from app.db.models import ClaudeAccount, ClaudeCooldown, ClaudeQuotaHistory, ClaudeResourceOrigin, ClaudeSessionOwner
from app.db.session import SessionLocal
from app.modules.claude.client import ClaudeClient
from app.modules.claude.credentials import ClaudeError
from app.modules.claude.failover import Refusal, record_refusals
from app.modules.claude.identity import require_current_identity
from app.modules.claude.observations import record_headers
from app.modules.claude.refusals import omit_refused_output, record_refused_response
from app.modules.claude.resources import ResourceOriginMissing, ResourceScope, record_keys, resolve_origins
from app.modules.claude.schemas import AccountState, AuthenticatedProfile, Credentials
from app.modules.claude.session import NativeSessionBinding
from app.modules.model_sources.forwarding import ModelSourceForwardingError
from tests.integration.test_claude_accounts import import_body, install_profile_stub
from tests.integration.test_claude_inference import MODEL, install_upstream, native_headers, pool
from tests.unit.test_claude_search import search_content

__all__ = ["pool"]
pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def stub(monkeypatch):
    install_profile_stub(monkeypatch)


async def start_reconnect(client, source_id):
    response = await client.post(
        "/api/claude-accounts/oauth/start",
        json={
            "name": "Claude test",
            "sourceId": source_id,
            "acknowledgeExclusiveRefresh": True,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["state"]


async def reconnect(client, monkeypatch, source_id, *, oauth=False, replace_identity=True, state=None):
    credentials = Credentials(
        access_token="replacement-access",
        refresh_token="replacement-refresh",
        expires_at=datetime.now(UTC) + timedelta(hours=1),
        scopes=["user:profile", "user:inference"],
    )
    if oauth:
        state = state or await start_reconnect(client, source_id)
        monkeypatch.setattr(ClaudeClient, "exchange", AsyncMock(return_value=credentials))
        return await client.post(
            "/api/claude-accounts/oauth/complete",
            json={
                "state": state,
                "code": "new-code",
                "replaceIdentity": replace_identity,
            },
        )
    return await client.post(
        f"/api/claude-accounts/{source_id}/reconnect",
        json={
            "acknowledgeExclusiveRefresh": True,
            "replaceIdentity": replace_identity,
            "credentials": {
                "claudeAiOauth": {
                    "accessToken": "replacement-access",
                    "refreshToken": "replacement-refresh",
                    "expiresAt": int(credentials.expires_at.timestamp() * 1000),
                    "scopes": credentials.scopes,
                    "subscriptionType": "claude_pro",
                    "rateLimitTier": "default_claude_pro",
                }
            },
        },
    )


@pytest.mark.parametrize("oauth", [False, True], ids=["import", "oauth"])
@pytest.mark.parametrize("identity_change", ["account", "organization", "none"])
async def test_explicit_replacement_preserves_account_and_retires_old_state(
    async_client, monkeypatch, oauth, identity_change
):
    source_id = (await async_client.post("/api/claude-accounts/import", json=import_body())).json()["id"]
    now = datetime.now(UTC).replace(tzinfo=None)
    async with SessionLocal() as session:
        row = await session.get(ClaudeAccount, source_id)
        assert row is not None
        row.routing_policy = "preserve"
        row.source.is_enabled = False
        row.source.max_concurrency = 3
        row.state_json = AccountState.model_validate(
            {
                "all_models": True,
                "selections": [{"model": "claude-opus-5"}],
                "reasoning_restrictions": {"claude-opus-5": ["high"]},
                "usage": {"five_hour": {"utilization": 100, "resets_at": datetime.now(UTC) + timedelta(hours=1)}},
                "usage_updated_at": datetime.now(UTC),
            }
        ).model_dump_json()
        session.add_all(
            [
                ClaudeCooldown(source_id=source_id, model="*", until=now + timedelta(hours=1)),
                ClaudeResourceOrigin(
                    resource_hash="old-resource",
                    source_id=source_id,
                    created_at=now,
                    expires_at=now + timedelta(days=1),
                ),
                ClaudeSessionOwner(scope_hash="old-session", source_id=source_id, expires_at=now + timedelta(hours=1)),
                ClaudeQuotaHistory(source_id=source_id, observed_at=now, window="five_hour", used_percent=100),
            ]
        )
        await session.commit()
    monkeypatch.setattr(
        ClaudeClient,
        "profile",
        AsyncMock(
            return_value=AuthenticatedProfile.model_validate(
                {
                    "account": {"uuid": "new-account" if identity_change == "account" else "access-secret"},
                    "organization": {"uuid": "new-org" if identity_change == "organization" else "org-test"},
                }
            )
        ),
    )
    response = await reconnect(async_client, monkeypatch, source_id, oauth=oauth)
    assert response.status_code == 200, response.text
    assert response.json()["id"] == source_id
    async with SessionLocal() as session:
        row = await session.get(ClaudeAccount, source_id)
        assert row is not None
        assert row.generation == 2 and row.credential_status == "ready"
        assert row.source.name == "Claude test" and row.source.is_enabled is False
        assert row.source.max_concurrency == 3 and row.routing_policy == "preserve"
        state = AccountState.model_validate_json(row.state_json)
        assert state.all_models and state.selections[0].model == "claude-opus-5"
        assert state.reasoning_restrictions == {"claude-opus-5": ["high"]}
        replaced = identity_change != "none"
        assert state.identity_generation == (2 if replaced else 1)
        assert (state.usage is None) == replaced
        assert (await session.get(ClaudeCooldown, (source_id, "*")) is None) == replaced
        assert (await session.get(ClaudeResourceOrigin, "old-resource")).identity_generation == 1
        if replaced:
            with pytest.raises(ResourceOriginMissing, match="replaced identity"):
                await resolve_origins(session, ("old-resource",))
        else:
            assert await resolve_origins(session, ("old-resource",)) == source_id
        assert (await session.get(ClaudeSessionOwner, "old-session") is None) == replaced
        assert await session.get(ClaudeQuotaHistory, (source_id, now, "five_hour")) is not None


async def test_stale_oauth_replacement_cannot_overwrite_new_login(async_client, monkeypatch):
    source_id = (await async_client.post("/api/claude-accounts/import", json=import_body())).json()["id"]
    state = await start_reconnect(async_client, source_id)
    assert (await reconnect(async_client, monkeypatch, source_id)).status_code == 200
    async with SessionLocal() as session:
        row = await session.get(ClaudeAccount, source_id)
        before = (row.credentials_encrypted, row.identity_fingerprint, row.state_json, row.generation)
    response = await reconnect(async_client, monkeypatch, source_id, oauth=True, state=state)
    assert response.status_code == 400 and "changed during reconnect" in response.text
    async with SessionLocal() as session:
        row = await session.get(ClaudeAccount, source_id)
        assert (row.credentials_encrypted, row.identity_fingerprint, row.state_json, row.generation) == before


async def test_replaced_identity_rejects_stale_resource_and_quota_writes(async_client, monkeypatch):
    source_id = (await async_client.post("/api/claude-accounts/import", json=import_body())).json()["id"]
    assert (await reconnect(async_client, monkeypatch, source_id)).status_code == 200
    with pytest.raises(ModelSourceForwardingError, match="replaced"):
        await require_current_identity(source_id, 1)
    await require_current_identity(source_id, 2)
    scope = ResourceScope("anonymous", "anthropic/claude-opus-5")
    keys = scope.keys(frozenset({"old-result"}))
    with pytest.raises(ModelSourceForwardingError):
        await record_keys(keys, source_id, identity_generation=1)
    now = datetime.now(UTC)
    await record_refusals(
        source_id, scope.model, (Refusal("account", now + timedelta(hours=1), "reset"),), credential_generation=1
    )
    await record_headers(
        source_id,
        1,
        {
            "anthropic-ratelimit-unified-5h-utilization": "1",
            "anthropic-ratelimit-unified-5h-reset": str(int((now + timedelta(hours=1)).timestamp())),
        },
        requested_at=now,
    )
    async with SessionLocal() as session:
        assert await session.get(ClaudeCooldown, (source_id, "*")) is None
        state = AccountState.model_validate_json((await session.get(ClaudeAccount, source_id)).state_json)
        assert not state.header_usage
        with pytest.raises(ResourceOriginMissing):
            await resolve_origins(session, keys)
    await record_keys(keys, source_id, identity_generation=2)
    async with SessionLocal() as session:
        assert await resolve_origins(session, keys) == source_id


async def test_duplicate_identity_replacement_rolls_back(async_client, monkeypatch):
    first = (await async_client.post("/api/claude-accounts/import", json=import_body())).json()["id"]
    other = import_body(refresh="another")
    assert (await async_client.post("/api/claude-accounts/import", json=other)).status_code == 200
    monkeypatch.setattr(
        ClaudeClient,
        "profile",
        AsyncMock(
            return_value=AuthenticatedProfile.model_validate(
                {
                    "account": {"uuid": "access-another"},
                    "organization": {"uuid": "org-test"},
                }
            )
        ),
    )
    response = await reconnect(async_client, monkeypatch, first)
    assert response.status_code == 400 and "already enrolled" in response.text
    async with SessionLocal() as session:
        row = await session.get(ClaudeAccount, first)
        assert row.generation == 1 and row.provider_account_uuid == "access-secret"


async def test_admission_cannot_rebind_old_identity_or_resource(async_client, monkeypatch):
    source_id = (await async_client.post("/api/claude-accounts/import", json=import_body())).json()["id"]
    scope = ResourceScope("client", MODEL)
    keys = scope.keys(frozenset({"old-resource"}))
    await record_keys(keys, source_id, identity_generation=1)
    assert (await reconnect(async_client, monkeypatch, source_id)).status_code == 200
    binding = NativeSessionBinding("client", "conversation", MODEL, None, identity_generation=1)
    with pytest.raises(ClaudeError, match="identity changed"):
        await binding.commit(source_id)
    binding = NativeSessionBinding("client", "conversation", MODEL, None, keys, identity_generation=2)
    with pytest.raises(ClaudeError, match="origin expired"):
        await binding.commit(source_id)
    binding = NativeSessionBinding("client", "conversation", MODEL, None, identity_generation=2)
    await binding.commit(source_id)


async def test_refusal_markers_survive_replacement_and_late_old_output(async_client, monkeypatch):
    source_id = (await async_client.post("/api/claude-accounts/import", json=import_body())).json()["id"]
    await record_refused_response("client", "resp_before", source_id, identity_generation=1)
    assert (await reconnect(async_client, monkeypatch, source_id)).status_code == 200
    await record_refused_response("client", "resp_late", source_id, identity_generation=1)
    await record_refused_response("client", "resp_current", source_id, identity_generation=2)
    payload = {
        "input": [
            {"id": f"resp_{name}_0", "role": "assistant", "content": "refused output"}
            for name in ("before", "late", "current")
        ]
    }
    assert await omit_refused_output(payload, "client") == {"input": []}
    assert await omit_refused_output(payload, "another-client") == payload


@pytest.mark.parametrize("path", ["/v1/responses", "/backend-api/codex/responses"])
async def test_replaced_identity_projects_completed_search_but_rejects_active_search(
    async_client, monkeypatch, pool, path
):
    captured, _ = install_upstream(monkeypatch, content=search_content())
    payload = {"model": MODEL, "input": "Search", "stream": False, "tools": [{"type": "web_search"}]}
    first = await async_client.post(path, json=payload)
    assert first.status_code == 200, first.text
    source_id = captured[0][0]
    assert (await reconnect(async_client, monkeypatch, source_id)).status_code == 200
    refreshed = await async_client.post(f"/api/claude-accounts/{source_id}/refresh")
    assert refreshed.status_code == 200, refreshed.text
    for other in pool:
        if other != source_id:
            await async_client.patch(f"/api/claude-accounts/{other}", json={"isEnabled": False})
    history = [{"role": "user", "content": "Search"}, *first.json()["output"]]
    active = await async_client.post(path, json={**payload, "input": history})
    assert active.status_code == 400 and "original account identity" in active.text
    assert len(captured) == 1
    completed = await async_client.post(
        path,
        json={
            **payload,
            "input": [*history, {"role": "user", "content": "Continue"}],
        },
    )
    assert completed.status_code == 200, completed.text
    assert captured[-1][0] == source_id
    import json

    sent = json.dumps(captured[-1][2]["messages"])
    assert "Web search: test" in sent
    assert "server_tool_use" not in sent and "upstream-owned-opaque-data" not in sent
    from app.core.crypto import TokenEncryptor
    from app.modules.claude.opaque import ClaudeOpaqueState

    token = next(item["encrypted_content"] for item in completed.json()["output"] if item["type"] == "reasoning")
    envelope = ClaudeOpaqueState(TokenEncryptor()).authenticate(token, client_scope="anonymous")
    assert envelope.identity_generation == 2


async def test_native_old_resources_cannot_follow_replacement(async_client, monkeypatch, pool):
    from app.modules.claude.profile import CLI_IDENTITY

    captured, _ = install_upstream(monkeypatch, content=search_content())
    payload = {
        "model": MODEL,
        "max_tokens": 100,
        "system": CLI_IDENTITY,
        "stream": True,
        "messages": [{"role": "user", "content": "Search"}],
    }
    first = await async_client.post("/v1/messages", headers=native_headers(), json=payload)
    assert first.status_code == 200, first.text
    source_id = captured[0][0]
    assert (await reconnect(async_client, monkeypatch, source_id)).status_code == 200
    assert (await async_client.post(f"/api/claude-accounts/{source_id}/refresh")).status_code == 200
    resumed = await async_client.post(
        "/v1/messages",
        headers=native_headers(),
        json={
            **payload,
            "messages": [
                *payload["messages"],
                {"role": "assistant", "content": search_content()},
                {"role": "user", "content": "Continue"},
            ],
        },
    )
    assert resumed.status_code == 400 and "belongs to a replaced identity" in resumed.text
    assert len(captured) == 1
