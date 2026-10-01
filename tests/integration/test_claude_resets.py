import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.db.models import ClaudeAccount, ClaudeCooldown, ClaudeResetOperation
from app.db.session import SessionLocal
from app.modules.claude.client import ClaudeClient
from app.modules.claude.credentials import ClaudeError
from app.modules.claude.failover import Refusal, record_refusals
from app.modules.claude.observations import record_headers
from app.modules.claude.reset_client import ClaimUnknown, ResetClient
from app.modules.claude.reset_repository import ResetRepository
from app.modules.claude.reset_schemas import ClaimAnswer, GrantStatus
from app.modules.claude.schemas import AuthenticatedProfile, BootstrapResponse, UsageSnapshot
from tests.integration.test_claude_accounts import import_body

pytestmark = pytest.mark.integration
ORG = "f737e84e-fd7d-4d90-8e19-a39f26b333cd"


def grants():
    return GrantStatus.model_validate(
        {
            "eligible": True,
            "at_limit": True,
            "grants": [
                {
                    "id": "test-grant",
                    "label": "Test reset",
                    "resets_total": 2,
                    "resets_left": 2,
                    "clears": ["five_hour"],
                    "paused": False,
                    "usable_now": True,
                    "use_requires_limit": True,
                }
            ],
        }
    )


@pytest.fixture
async def reset_account(async_client, monkeypatch):
    monkeypatch.setattr(
        ClaudeClient,
        "bootstrap",
        AsyncMock(
            return_value=BootstrapResponse.model_validate(
                {"oauth_account": {"account_uuid": "user", "organization_uuid": ORG}}
            )
        ),
    )
    monkeypatch.setattr(
        ClaudeClient,
        "profile",
        AsyncMock(
            return_value=AuthenticatedProfile.model_validate(
                {
                    "account": {"uuid": "user"},
                    "organization": {"uuid": ORG},
                }
            )
        ),
    )
    monkeypatch.setattr(ClaudeClient, "usage", AsyncMock(return_value=UsageSnapshot()))
    monkeypatch.setattr(ResetClient, "grants", AsyncMock(return_value=grants()))
    claim = AsyncMock(return_value=ClaimAnswer(result="reset", resets_left=1, cleared=["five_hour"]))
    monkeypatch.setattr(ResetClient, "claim", claim)
    imported = await async_client.post("/api/claude-accounts/import", json=import_body())
    assert imported.status_code == 200, imported.text
    return imported.json()["id"], claim


def request(**extra):
    return {"grantId": "test-grant", "operationId": str(uuid4()), "confirmed": True, **extra}


async def test_confirmed_reset_replay_and_selective_reconciliation(async_client, reset_account):
    source, claim = reset_account
    now = datetime.now(UTC)
    await record_refusals(
        source,
        "anthropic/test",
        (
            Refusal("account", now + timedelta(hours=2), "reset", "five_hour"),
            Refusal("account", now + timedelta(hours=80), "reset", "seven_day"),
            Refusal("model", now + timedelta(hours=4), "default", "entitlement"),
        ),
        requested_at=now,
    )
    await record_headers(source, 1, {"anthropic-ratelimit-unified-5h-utilization": "1"}, requested_at=now)
    payload = request()
    path = f"/api/claude-accounts/{source}/reset-grants"
    status = await async_client.get(path)
    assert status.json()["status"]["grants"][0]["resets_left"] == 2
    first = await async_client.post(path + "/consume", json=payload)
    assert first.status_code == 200, first.text
    assert first.json()["operation"]["result"]["result"] == "reset"
    repeated = await async_client.post(path + "/consume", json=payload)
    assert repeated.status_code == 200 and claim.await_count == 1
    # A late refusal from a pre-reset physical request must not restore cleared evidence.
    await record_refusals(
        source,
        "anthropic/test",
        (Refusal("account", now + timedelta(hours=100), "reset", "five_hour"),),
        requested_at=now,
    )
    async with SessionLocal() as session:
        row = await session.get(ClaudeCooldown, (source, "*"))
        assert row.until.replace(tzinfo=UTC) == now + timedelta(hours=80)
        assert '"five_hour"' not in row.evidence_json
        assert await session.get(ClaudeCooldown, (source, "anthropic/test")) is not None


async def test_unknown_same_id_and_expired_acknowledgement(async_client, reset_account):
    source, claim = reset_account
    claim.side_effect = ClaimUnknown("unknown")
    payload = request()
    path = f"/api/claude-accounts/{source}/reset-grants"
    response = await async_client.post(path + "/consume", json=payload)
    assert response.status_code == 200 and response.json()["operation"]["result"] is None
    assert (await async_client.post(path + "/consume", json=request())).status_code == 400
    assert claim.await_count == 1
    await async_client.post(path + "/consume", json=payload)
    assert claim.await_count == 2
    assert claim.call_args_list[0].args[-1] == claim.call_args_list[1].args[-1]
    async with SessionLocal() as session:
        row = await session.get(ClaudeResetOperation, payload["operationId"])
        row.created_at -= timedelta(minutes=11)
        await session.commit()
    assert (await async_client.post(path + "/consume", json=payload)).status_code == 400
    assert (await async_client.post(path + "/consume", json=request())).status_code == 400
    visible = (await async_client.get(path)).json()["operations"]
    assert visible[0]["result"] is None
    claim.side_effect = None
    result = await async_client.post(path + "/consume", json=request(acknowledgeUncertain=True))
    assert result.status_code == 200 and claim.await_count == 3


async def test_concurrent_claims_do_not_duplicate(async_client, reset_account):
    source, claim = reset_account
    started, release = asyncio.Event(), asyncio.Event()

    async def delayed(*args):
        started.set()
        await release.wait()
        return ClaimAnswer(result="reset", cleared=["five_hour"])

    claim.side_effect = delayed
    path = f"/api/claude-accounts/{source}/reset-grants/consume"
    payload = request()
    task = asyncio.create_task(async_client.post(path, json=payload))
    try:
        await asyncio.wait_for(started.wait(), 5)
        other = await async_client.post(path, json=payload)
        assert other.status_code == 400 and claim.await_count == 1
        different = await async_client.post(path, json=request())
        assert different.status_code == 400 and claim.await_count == 1
        release.set()
        assert (await task).status_code == 200
    finally:
        release.set()
        if not task.done():
            task.cancel()
        await asyncio.gather(task, return_exceptions=True)


async def test_status_outage_preserves_pending_and_refresh_failure_is_not_failed_spend(
    async_client, reset_account, monkeypatch
):
    source, claim = reset_account
    path = f"/api/claude-accounts/{source}/reset-grants"
    monkeypatch.setattr(ClaudeClient, "usage", AsyncMock(side_effect=ClaudeError("offline")))
    result = await async_client.post(path + "/consume", json=request())
    assert result.json()["operation"]["result"]["result"] == "reset"
    assert result.json()["refreshComplete"] is False
    claim.side_effect = ClaimUnknown("unknown")
    await async_client.post(path + "/consume", json=request())
    monkeypatch.setattr(ResetClient, "grants", AsyncMock(side_effect=ClaudeError("offline")))
    status = (await async_client.get(path)).json()
    assert status["status"] is None and status["error"]
    assert any(op["result"] is None for op in status["operations"])


async def test_confirmation_and_fresh_eligibility_required(async_client, reset_account, monkeypatch):
    source, claim = reset_account
    path = f"/api/claude-accounts/{source}/reset-grants/consume"
    assert (await async_client.post(path, json=request(confirmed=False))).status_code == 422
    unavailable = grants()
    unavailable.grants[0].resets_left = 0
    monkeypatch.setattr(ResetClient, "grants", AsyncMock(return_value=unavailable))
    assert (await async_client.post(path, json=request())).status_code == 400
    assert claim.await_count == 0


async def test_post_reset_refusal_and_legacy_restriction_survive(async_client, reset_account):
    source, claim = reset_account
    now = datetime.now(UTC)
    async with SessionLocal() as session:
        session.add(
            ClaudeCooldown(source_id=source, model="legacy", until=(now + timedelta(hours=9)).replace(tzinfo=None))
        )
        await session.commit()

    async def concurrent(*args):
        await record_refusals(
            source,
            "test",
            (Refusal("account", now + timedelta(hours=3), "reset", "five_hour"),),
            requested_at=datetime.now(UTC),
        )
        return ClaimAnswer(result="reset", cleared=["five_hour"])

    claim.side_effect = concurrent
    result = await async_client.post(f"/api/claude-accounts/{source}/reset-grants/consume", json=request())
    assert result.status_code == 200
    async with SessionLocal() as session:
        assert await session.get(ClaudeCooldown, (source, "*")) is not None
        assert await session.get(ClaudeCooldown, (source, "legacy")) is not None


async def test_settlement_failure_leaves_durable_unknown(async_client, reset_account, monkeypatch):
    source, claim = reset_account
    monkeypatch.setattr(ResetRepository, "settle", AsyncMock(side_effect=ClaudeError("Settlement unavailable")))
    payload = request()
    result = await async_client.post(f"/api/claude-accounts/{source}/reset-grants/consume", json=payload)
    assert result.status_code == 400 and claim.await_count == 1
    async with SessionLocal() as session:
        row = await session.get(ClaudeResetOperation, payload["operationId"])
        assert row.result_json is None


async def test_write_authorization_precedes_claim(async_client, app_instance, reset_account):
    from fastapi import HTTPException

    from app.core.auth.dependencies import require_dashboard_write_access

    source, claim = reset_account

    async def deny():
        raise HTTPException(status_code=403)

    app_instance.dependency_overrides[require_dashboard_write_access] = deny
    try:
        response = await async_client.post(f"/api/claude-accounts/{source}/reset-grants/consume", json=request())
        assert response.status_code == 403 and claim.await_count == 0
    finally:
        app_instance.dependency_overrides.pop(require_dashboard_write_access)


async def test_cancelled_claim_keeps_lease_and_intent(async_client, reset_account):
    source, claim = reset_account
    started = asyncio.Event()
    payload = request()

    async def stalled(*args):
        async with SessionLocal() as session:
            row = await session.get(ClaudeResetOperation, payload["operationId"])
            assert row is not None and row.result_json is None
        started.set()
        await asyncio.Event().wait()

    claim.side_effect = stalled
    task = asyncio.create_task(async_client.post(f"/api/claude-accounts/{source}/reset-grants/consume", json=payload))
    try:
        await asyncio.wait_for(started.wait(), 5)
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
    async with SessionLocal() as session:
        row = await session.get(ClaudeResetOperation, payload["operationId"])
        assert row.result_json is None
        assert row.lease_until > datetime.now(UTC).replace(tzinfo=None)


async def test_deleted_account_does_not_erase_claim_evidence(async_client, reset_account):
    source, claim = reset_account
    claim.side_effect = ClaimUnknown("unknown")
    payload = request()
    await async_client.post(f"/api/claude-accounts/{source}/reset-grants/consume", json=payload)
    assert (await async_client.delete(f"/api/claude-accounts/{source}")).status_code in (200, 204)
    async with SessionLocal() as session:
        assert await session.get(ClaudeResetOperation, payload["operationId"]) is not None


async def test_late_usage_does_not_restore_cleared_quota(async_client, reset_account, monkeypatch):
    from app.modules.claude.quota import quota_status
    from app.modules.claude.schemas import AccountState, QuotaWindow

    source, _ = reset_account
    before = datetime.now(UTC)
    async with SessionLocal() as session:
        row = await session.get(ClaudeAccount, source)
        state = AccountState.model_validate_json(row.state_json)
        state.usage = UsageSnapshot(five_hour=QuotaWindow(utilization=100), seven_day=QuotaWindow(utilization=70))
        state.usage_updated_at = before
        state.usage_requested_at = before
        row.state_json = state.model_dump_json()
        await session.commit()
    monkeypatch.setattr(ClaudeClient, "usage", AsyncMock(side_effect=ClaudeError("offline")))
    await async_client.post(f"/api/claude-accounts/{source}/reset-grants/consume", json=request())
    await record_headers(source, 1, {"anthropic-ratelimit-unified-5h-utilization": "1"}, requested_at=before)
    async with SessionLocal() as session:
        row = await session.get(ClaudeAccount, source)
        state = AccountState.model_validate_json(row.state_json)
        windows = quota_status(state, now=datetime.now(UTC)).windows
        assert windows[0].utilization is None and not windows[0].exhausted
        assert windows[1].utilization == 70


async def test_terminal_result_first_wins_and_wrong_grant_rejected(async_client, reset_account):
    source, claim = reset_account
    payload = request()
    path = f"/api/claude-accounts/{source}/reset-grants/consume"
    await async_client.post(path, json=payload)
    async with SessionLocal() as session:
        row = await ResetRepository(session).settle(
            source,
            payload["operationId"],
            ClaimAnswer(result="ineligible"),
        )
        assert ClaimAnswer.model_validate_json(row.result_json).result == "reset"
    payload["grantId"] = "other"
    assert (await async_client.post(path, json=payload)).status_code == 400
    assert claim.await_count == 1


async def test_retry_preserves_evidence_after_original_reset(async_client, reset_account):
    source, claim = reset_account
    claim.side_effect = ClaimUnknown("reply lost")
    payload = request()
    path = f"/api/claude-accounts/{source}/reset-grants/consume"
    assert (await async_client.post(path, json=payload)).status_code == 200
    after_original = datetime.now(UTC)
    await record_refusals(
        source,
        "test",
        (Refusal("account", after_original + timedelta(hours=3), "reset", "five_hour"),),
        requested_at=after_original,
    )
    claim.side_effect = None
    assert (await async_client.post(path, json=payload)).status_code == 200
    assert claim.await_count == 2
    async with SessionLocal() as session:
        row = await session.get(ClaudeCooldown, (source, "*"))
        assert row is not None and '"five_hour"' in row.evidence_json


async def test_changed_profile_prevents_spend(async_client, reset_account, monkeypatch):
    source, claim = reset_account
    monkeypatch.setattr(
        ClaudeClient,
        "profile",
        AsyncMock(
            return_value=AuthenticatedProfile.model_validate(
                {
                    "account": {"uuid": "different-user"},
                    "organization": {"uuid": ORG},
                }
            )
        ),
    )
    response = await async_client.post(f"/api/claude-accounts/{source}/reset-grants/consume", json=request())
    assert response.status_code == 400 and claim.await_count == 0
