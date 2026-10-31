from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from app.db.models import ClaudeAccount, ClaudePendingReconnect
from app.db.session import SessionLocal
from app.modules.claude.client import ClaudeClient
from app.modules.claude.schemas import AccountState, AuthenticatedProfile, BootstrapResponse, SubscriptionMetadata
from tests.integration.test_claude_accounts import import_body
from tests.integration.test_claude_identity_replacement import reconnect

pytestmark = pytest.mark.integration


def profile(organization: str, organization_name: str) -> AsyncMock:
    return AsyncMock(
        return_value=AuthenticatedProfile.model_validate(
            {
                "account": {"uuid": "access-secret", "email": "doca@example.com"},
                "organization": {"uuid": organization, "name": organization_name},
            }
        )
    )


@pytest.fixture
async def max_account(async_client, monkeypatch) -> str:
    monkeypatch.setattr(ClaudeClient, "profile", profile("org-max", "Max Org"))
    created = await async_client.post("/api/claude-accounts/import", json=import_body())
    assert created.status_code == 200, created.text
    assert (created.json()["accountEmail"], created.json()["organizationName"]) == ("doca@example.com", "Max Org")
    source_id = created.json()["id"]
    async with SessionLocal() as session:
        row = await session.get(ClaudeAccount, source_id)
        row.state_json = AccountState(
            subscription=SubscriptionMetadata(
                rate_limit_tier="default_claude_max_5x", source="bootstrap", observed_at=datetime.now(UTC)
            )
        ).model_dump_json()
        await session.commit()
    monkeypatch.setattr(ClaudeClient, "profile", profile("org-pro", "Pro Org"))
    return source_id


async def saved_credentials(source_id: str) -> tuple[bytes, int]:
    async with SessionLocal() as session:
        row = await session.get(ClaudeAccount, source_id)
        return row.credentials_encrypted, row.generation


async def test_changed_identity_is_held_with_a_comparison_and_confirmed_once(async_client, monkeypatch, max_account):
    before = await saved_credentials(max_account)
    held = await reconnect(async_client, monkeypatch, max_account, confirm=False)

    assert held.status_code == 409, held.text
    error = held.json()["error"]
    assert error["code"] == "claude_reconnect_organization_changed"
    details = error["details"]
    assert details["saved"] == {"email": "doca@example.com", "organization": "Max Org", "plan": "max"}
    assert details["incoming"] == {"email": "doca@example.com", "organization": "Pro Org", "plan": "pro"}
    assert "replacement" not in held.text
    assert await saved_credentials(max_account) == before

    path = f"/api/claude-accounts/{max_account}/pending-reconnects/{details['pendingId']}/confirm"
    confirmed = await async_client.post(path)
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["organizationName"] == "Pro Org"
    assert confirmed.json()["planType"] == "pro"
    assert (await saved_credentials(max_account))[1] == before[1] + 1

    again = await async_client.post(path)
    assert again.status_code == 400 and "no longer awaiting confirmation" in again.text


async def test_oauth_hold_reads_the_incoming_plan(async_client, monkeypatch, max_account):
    async def bootstrap(_self, token, _version):
        return BootstrapResponse.model_validate(
            {
                "oauth_account": {
                    "account_uuid": "access-secret",
                    "organization_uuid": "org-pro",
                    "organization_rate_limit_tier": "default_claude_pro",
                }
            }
        )

    monkeypatch.setattr(ClaudeClient, "bootstrap", bootstrap)
    held = await reconnect(async_client, monkeypatch, max_account, oauth=True, confirm=False)

    assert held.status_code == 409, held.text
    assert held.json()["error"]["details"]["incoming"]["plan"] == "pro"


async def test_discarded_expired_or_stale_holds_cannot_replace_credentials(async_client, monkeypatch, max_account):
    before = await saved_credentials(max_account)

    discarded = (await reconnect(async_client, monkeypatch, max_account, confirm=False)).json()["error"]["details"]
    pending_path = f"/api/claude-accounts/{max_account}/pending-reconnects/{discarded['pendingId']}"
    assert (await async_client.delete(pending_path)).status_code == 204
    assert (await async_client.post(f"{pending_path}/confirm")).status_code == 400

    expired = (await reconnect(async_client, monkeypatch, max_account, confirm=False)).json()["error"]["details"]
    async with SessionLocal() as session:
        pending = await session.get(ClaudePendingReconnect, expired["pendingId"])
        pending.expires_at = datetime.now(UTC).replace(tzinfo=None) - timedelta(seconds=1)
        await session.commit()
    expired_path = f"/api/claude-accounts/{max_account}/pending-reconnects/{expired['pendingId']}/confirm"
    assert (await async_client.post(expired_path)).status_code == 400

    stale = (await reconnect(async_client, monkeypatch, max_account, confirm=False)).json()["error"]["details"]
    async with SessionLocal() as session:
        row = await session.get(ClaudeAccount, max_account)
        row.generation += 1
        await session.commit()
    stale_path = f"/api/claude-accounts/{max_account}/pending-reconnects/{stale['pendingId']}/confirm"
    response = await async_client.post(stale_path)
    assert response.status_code == 400 and "changed during reconnect" in response.text
    credentials, generation = await saved_credentials(max_account)
    assert credentials == before[0] and generation == before[1] + 1


async def test_matching_identity_completes_without_confirmation(async_client, monkeypatch, max_account):
    monkeypatch.setattr(ClaudeClient, "profile", profile("org-max", "Max Org"))

    response = await reconnect(async_client, monkeypatch, max_account, confirm=False)

    assert response.status_code == 200, response.text
    async with SessionLocal() as session:
        assert (await session.get(ClaudeAccount, max_account)).generation == 2
        assert (await session.scalar(ClaudePendingReconnect.__table__.select())) is None
