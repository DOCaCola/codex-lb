from dataclasses import replace
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from pydantic import JsonValue

from app.db.models import ClaudeAccount
from app.db.session import SessionLocal
from app.modules.api_keys.service import ApiKeyData
from app.modules.claude.client import ClaudeClient
from app.modules.claude.routing import ClaudePoolUnavailable, select_account
from app.modules.claude.schemas import AccountState, CatalogModel, QuotaWindow, UsageSnapshot
from tests.claude_json_helpers import array, at
from tests.integration import test_claude_accounts as account_fixtures
from tests.integration.test_claude_accounts import import_body

pytestmark = pytest.mark.integration
MODEL = "anthropic/claude-opus-5"


def key(**overrides):
    value = ApiKeyData(
        id="key-a",
        name="test",
        key_prefix="test",
        allowed_models=None,
        enforced_model=None,
        enforced_reasoning_effort=None,
        enforced_service_tier=None,
        expires_at=None,
        is_active=True,
        created_at=datetime.now(UTC),
        last_used_at=None,
    )
    return replace(value, **overrides)


@pytest.fixture
async def pool(async_client, monkeypatch):
    account_fixtures.install_profile_stub(monkeypatch)
    monkeypatch.setattr(
        ClaudeClient,
        "catalog",
        AsyncMock(
            return_value=[
                CatalogModel(id="claude-opus-5", display_name="Opus"),
                CatalogModel(id="claude-sonnet-5", display_name="Sonnet"),
            ]
        ),
    )
    monkeypatch.setattr(ClaudeClient, "usage", AsyncMock(return_value=UsageSnapshot()))
    ids = []
    for token in ("account-a", "account-b"):
        response = await async_client.post("/api/claude-accounts/import", json=import_body(refresh=token))
        source_id = response.json()["id"]
        ids.append(source_id)
        await async_client.post(f"/api/claude-accounts/{source_id}/refresh")
        await async_client.patch(
            f"/api/claude-accounts/{source_id}",
            json={
                "selections": [
                    {"model": "claude-opus-5"},
                    {"model": "claude-sonnet-5"},
                ]
            },
        )
    return ids


async def choose(*, model=MODEL, api_key=None, **kwargs):
    async with SessionLocal() as session:
        return (await select_account(session, model, api_key, conversation_id="conversation", **kwargs)).source_id


async def test_affinity_survives_new_session_and_excludes_account(pool):
    selected = await choose(api_key=key())
    assert await choose(api_key=key()) == selected
    assert await choose(api_key=key(), excluded_source_ids=frozenset({selected})) == next(
        value for value in pool if value != selected
    )


async def test_permissions_applied_before_owner_or_affinity(pool):
    scoped = key(source_assignment_scope_enabled=True, assigned_source_ids=[pool[1]])
    assert await choose(api_key=scoped) == pool[1]
    with pytest.raises(ClaudePoolUnavailable) as error:
        await choose(api_key=scoped, owner_source_id=pool[0])
    assert error.value.code == "previous_response_owner_unavailable"
    with pytest.raises(ClaudePoolUnavailable):
        await choose(api_key=replace(scoped, assigned_source_ids=[]))
    with pytest.raises(ClaudePoolUnavailable) as error:
        await choose(api_key=key(allowed_models=["gpt-6-astra"]))
    assert error.value.code == "model_not_allowed"
    with pytest.raises(ClaudePoolUnavailable):
        await choose(api_key=key(enforced_model="gpt-6-astra"))


async def test_bound_owner_not_replaced_when_paused(pool, async_client):
    assert await choose(owner_source_id=pool[0]) == pool[0]
    await async_client.patch(f"/api/claude-accounts/{pool[0]}", json={"isEnabled": False})
    assert await choose() == pool[1]
    with pytest.raises(ClaudePoolUnavailable) as error:
        await choose(owner_source_id=pool[0])
    assert error.value.code == "previous_response_owner_unavailable"


@pytest.mark.parametrize("condition", ["reauth", "uncertain", "refresh", "backoff", "quota"])
async def test_unavailable_owner_cannot_cross_account(pool, condition):
    async with SessionLocal() as session:
        row = await session.get(ClaudeAccount, pool[0])
        assert row is not None
        if condition == "reauth":
            row.credential_status = "reauth_required"
        elif condition == "uncertain":
            row.credential_status = "uncertain"
        elif condition == "refresh":
            row.refresh_intent = "other-worker"
        elif condition == "backoff":
            row.retry_at = datetime.now(UTC).replace(tzinfo=None) + timedelta(minutes=5)
        else:
            state = AccountState.model_validate_json(row.state_json)
            state.usage = UsageSnapshot(
                seven_day_opus=QuotaWindow(utilization=100, resets_at=datetime.now(UTC) + timedelta(hours=1))
            )
            state.usage_updated_at = datetime.now(UTC)
            row.state_json = state.model_dump_json()
        await session.commit()
    assert await choose() == pool[1]
    with pytest.raises(ClaudePoolUnavailable):
        await choose(owner_source_id=pool[0])
    if condition == "quota":
        assert await choose(model="anthropic/claude-sonnet-5", owner_source_id=pool[0]) == pool[0]


async def test_empty_or_disabled_pool_is_explicit_error(pool, async_client):
    for source_id in pool:
        await async_client.patch(f"/api/claude-accounts/{source_id}", json={"isEnabled": False})
    with pytest.raises(ClaudePoolUnavailable) as error:
        await choose()
    assert error.value.code == "claude_pool_unavailable"


async def test_rendezvous_distribution_and_order_independence(pool):
    from app.modules.claude.routing import _score

    chosen = set()
    for index in range(100):
        conversation = f"conversation-{index}"
        first = max(pool, key=lambda source: _score(source, "key", conversation, MODEL))
        second = max(reversed(pool), key=lambda source: _score(source, "key", conversation, MODEL))
        assert first == second
        chosen.add(first)
    assert chosen == set(pool)


async def test_prepare_uses_provider_credentials_and_preserves_logical_history(pool):
    from app.modules.claude.dispatch import ClaudeDispatchPreparer
    from app.modules.claude.repository import ClaudeRepository

    logical: dict[str, JsonValue] = {
        "model": MODEL,
        "max_tokens": 100,
        "system": "Caller instructions",
        "messages": [{"role": "user", "content": "Hello"}],
    }
    async with SessionLocal() as session:
        prepared = await ClaudeDispatchPreparer(ClaudeRepository(session)).prepare(
            logical,
            key(),
            conversation_id="thread",
            incoming_headers={"Authorization": "Bearer caller-secret"},
            endpoint="messages",
            translated=True,
        )
        assert prepared.url == "https://api.anthropic.com/v1/messages?beta=true"
        assert prepared.body["model"] == "claude-opus-5"
        assert prepared.headers["authorization"] in {"Bearer access-account-a", "Bearer access-account-b"}
        assert at(prepared.body, "messages", 1) == {
            "role": "system",
            "content": [{"type": "text", "text": "Caller instructions"}],
        }
        assert "access-secret" not in repr(prepared)
        assert "Caller instructions" not in repr(prepared)
    assert logical["model"] == MODEL
    assert len(array(logical["messages"])) == 1


async def test_prepare_rechecks_pause_after_credential_refresh(pool):
    from app.modules.claude.dispatch import ClaudeDispatchPreparer
    from app.modules.claude.repository import ClaudeRepository
    from app.modules.claude.schemas import Credentials

    async with SessionLocal() as session:
        row = await session.get(ClaudeAccount, pool[0])
        assert row is not None
        from app.core.crypto import TokenEncryptor
        from app.modules.claude.credentials import decrypt_credentials, encrypt_credentials

        credentials = decrypt_credentials(row.credentials_encrypted, TokenEncryptor())
        expired = credentials.model_copy(update={"expires_at": datetime.now(UTC) - timedelta(minutes=1)})
        row.credentials_encrypted = encrypt_credentials(expired, TokenEncryptor())
        row.expires_at = expired.expires_at.replace(tzinfo=None)
        await session.commit()

    async def rotate(_credentials):
        async with SessionLocal() as session:
            row = await session.get(ClaudeAccount, pool[0])
            assert row is not None
            row.source.is_enabled = False
            await session.commit()
        return Credentials(
            access_token="rotated",
            refresh_token="rotated-refresh",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            scopes=["user:inference"],
        )

    client = ClaudeClient()
    client.refresh = AsyncMock(side_effect=rotate)
    async with SessionLocal() as session:
        with pytest.raises(ClaudePoolUnavailable):
            await ClaudeDispatchPreparer(ClaudeRepository(session), client).prepare(
                {"model": MODEL, "max_tokens": 100, "messages": [{"role": "user", "content": "Hello"}]},
                key(),
                conversation_id="thread",
                incoming_headers={},
                endpoint="messages",
                translated=True,
                owner_source_id=pool[0],
            )
    client.refresh.assert_awaited_once()


async def test_invalid_payload_rejected_before_token_refresh(pool):
    from app.modules.claude.credentials import ClaudeError
    from app.modules.claude.dispatch import ClaudeDispatchPreparer
    from app.modules.claude.repository import ClaudeRepository

    async with SessionLocal() as session:
        preparer = ClaudeDispatchPreparer(ClaudeRepository(session))
        preparer.auth.credentials = AsyncMock()
        with pytest.raises(ClaudeError):
            await preparer.prepare(
                {"model": MODEL, "max_tokens": 100, "messages": []},
                key(),
                conversation_id="thread",
                incoming_headers={},
                endpoint="messages",
                translated=True,
            )
        preparer.auth.credentials.assert_not_awaited()
