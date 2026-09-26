import asyncio
import json
from datetime import UTC, timedelta

import pytest
from sqlalchemy import select, update

from app.db.models import QuotaWebhookBaseline, QuotaWebhookConfig, QuotaWebhookDelivery
from app.db.session import SessionLocal
from app.modules.accounts.repository import AccountsRepository
from app.modules.quota_webhook.repository import claim, now_utc, redemption_intent, settle
from app.modules.usage.repository import UsageRepository, UsageWindowWrite
from tests.integration.test_usage_api import _make_account

pytestmark = pytest.mark.integration
PATH = "/api/settings/quota-reset-webhook"


@pytest.fixture
async def configured(async_client):
    response = await async_client.put(
        PATH,
        json={
            "enabled": True,
            "kinds": ["scheduled", "unexpected"],
            "url": "https://example.com/secret-path",
            "signingSecret": "test-signing-secret",
        },
    )
    assert response.status_code == 200, response.text
    async with SessionLocal() as session:
        await AccountsRepository(session).upsert(_make_account("webhook-a", "a@example.com"))
        await AccountsRepository(session).upsert(_make_account("webhook-b", "b@example.com"))
    return now_utc() + timedelta(seconds=1)


async def snapshot(at, percent, *, account="webhook-a", window="secondary", reset=None):
    async with SessionLocal() as session:
        await UsageRepository(session).add_account_snapshot(
            account,
            [
                UsageWindowWrite(
                    window=window,
                    used_percent=percent,
                    reset_at=reset or int((at + timedelta(days=3)).replace(tzinfo=UTC).timestamp()),
                    window_minutes=10080,
                )
            ],
            recorded_at=at,
        )


async def deliveries():
    async with SessionLocal() as session:
        return list(await session.scalars(select(QuotaWebhookDelivery).order_by(QuotaWebhookDelivery.created_at)))


async def test_settings_mask_secrets_and_test_delivery(async_client, configured):
    response = await async_client.get(PATH)
    assert response.json()["urlConfigured"] and response.json()["signingSecretConfigured"]
    assert "secret-path" not in response.text and "test-signing-secret" not in response.text
    async with SessionLocal() as session:
        config = await session.get(QuotaWebhookConfig, 1)
        assert b"secret-path" not in config.url_encrypted
    response = await async_client.post(PATH + "/test")
    assert response.status_code == 200
    row = (await deliveries())[0]
    assert json.loads(row.payload)["type"] == "quota.test"
    assert row.id == response.json()["eventId"]


async def test_reveal_saved_destination_is_explicit_and_not_cached(async_client, configured):
    response = await async_client.get(PATH + "/destination")
    assert response.status_code == 200
    assert response.json() == {"url": "https://example.com/secret-path"}
    assert response.headers["cache-control"] == "no-store"
    assert "secret-path" not in (await async_client.get(PATH)).text


async def test_reveal_absent_destination(async_client):
    response = await async_client.get(PATH + "/destination")
    assert response.status_code == 200
    assert response.json() == {"url": None}


async def test_reset_dedup_and_second_same_deadline(configured):
    start = configured
    reset = int((start + timedelta(days=3)).replace(tzinfo=UTC).timestamp())
    await snapshot(start, 80, reset=reset)
    await snapshot(start + timedelta(seconds=60), 0, reset=reset)
    await snapshot(start + timedelta(seconds=90), 0, reset=reset)
    await snapshot(start + timedelta(seconds=120), 60, reset=reset)
    await snapshot(start + timedelta(seconds=150), 0, reset=reset)
    rows = await deliveries()
    assert len(rows) == 2 and rows[0].id != rows[1].id
    assert all(json.loads(row.payload)["kind"] == "unexpected" for row in rows)
    assert "a@example.com" not in rows[0].payload


async def test_multiple_accounts_not_batched_and_old_samples_ignored(configured):
    for account in ["webhook-a", "webhook-b"]:
        reset = int((configured + timedelta(days=3)).replace(tzinfo=UTC).timestamp())
        await snapshot(configured, 90, account=account, reset=reset)
        await snapshot(configured + timedelta(seconds=60), 0, account=account, reset=reset)
        await snapshot(configured + timedelta(seconds=10), 95, account=account, reset=reset)
        await snapshot(configured + timedelta(seconds=90), 0, account=account, reset=reset)
    rows = await deliveries()
    assert len(rows) == 2
    assert {json.loads(row.payload)["account_id"] for row in rows} == {"webhook-a", "webhook-b"}


async def test_delivery_claim_retry_and_destination_change(async_client, configured):
    await async_client.post(PATH + "/test")
    async with SessionLocal() as session:
        first = await claim(session)
    async with SessionLocal() as session:
        assert await claim(session) is None
        await settle(session, first, status=503, error="http_error", retryable=True)
        await session.execute(update(QuotaWebhookDelivery).values(next_at=now_utc() - timedelta(seconds=1)))
        await session.commit()
    async with SessionLocal() as session:
        retry = await claim(session)
    assert retry.event_id == first.event_id and retry.payload == first.payload
    assert retry.lease_id != first.lease_id
    await async_client.put(PATH, json={"enabled": False, "kinds": ["scheduled"]})
    async with SessionLocal() as session:
        await settle(session, retry, status=200, error=None, retryable=False)
        assert await claim(session) is None
    assert (await deliveries())[0].status == "cancelled"


async def test_snapshot_race_enqueues_once(configured):
    reset = int((configured + timedelta(days=3)).replace(tzinfo=UTC).timestamp())
    await snapshot(configured, 80, reset=reset)
    await asyncio.gather(*(snapshot(configured + timedelta(seconds=60), 0, reset=reset) for _ in range(3)))
    assert len(await deliveries()) == 1


async def test_redemption_clears_baseline(configured):
    from app.db.models import Account

    async with SessionLocal() as session:
        await session.execute(update(Account).where(Account.id == "webhook-a").values(chatgpt_account_id="upstream"))
        await session.commit()
    await snapshot(configured, 90)
    async with SessionLocal() as session:
        await redemption_intent(session, "upstream")
        assert await session.get(QuotaWebhookBaseline, ("webhook-a", "secondary")) is None
    await snapshot(configured + timedelta(minutes=20), 0)
    assert await deliveries() == []


async def test_invalid_url_and_empty_filter_rejected(async_client):
    for url in ["http://example.com", "https://127.0.0.1"]:
        response = await async_client.put(PATH, json={"enabled": True, "kinds": ["scheduled"], "url": url})
        assert response.status_code == 400
    response = await async_client.put(PATH, json={"enabled": True, "kinds": []})
    assert response.status_code == 422


async def test_write_and_test_require_ops_permission(app_instance, async_client, monkeypatch):
    from app.core.auth.dashboard_access import Permission
    from tests.integration.test_dashboard_permission_gates import _principal_without, _use_principal

    _use_principal(app_instance, monkeypatch, _principal_without(Permission.SECURITY_WRITE, Permission.OPS_WRITE))
    assert (await async_client.get(PATH)).status_code == 200
    response = await async_client.put(PATH, json={"enabled": False, "kinds": ["scheduled"]})
    assert response.status_code == 403
    assert (await async_client.post(PATH + "/test")).status_code == 403
    assert (await async_client.get(PATH + "/destination")).status_code == 403


async def test_ops_only_user_can_save_without_step_up(app_instance, async_client, monkeypatch):
    from dataclasses import replace
    from unittest.mock import AsyncMock

    import app.core.auth.dependencies as auth
    from app.core.auth.dashboard_access import Permission
    from tests.integration.test_dashboard_permission_gates import _principal_without, _use_principal

    principal = replace(_principal_without(Permission.SECURITY_WRITE), user_id="operator-without-factor")
    _use_principal(app_instance, monkeypatch, principal)
    step_up = AsyncMock(side_effect=AssertionError("Operational settings must not require step-up"))
    monkeypatch.setattr(auth, "ensure_step_up", step_up)
    response = await async_client.put(
        PATH, json={"enabled": True, "kinds": ["scheduled"], "url": "https://example.com/webhook"}
    )
    assert response.status_code == 200, response.text
    assert (await async_client.post(PATH + "/test")).status_code == 200
    assert (await async_client.get(PATH + "/destination")).status_code == 200
    step_up.assert_not_called()


async def test_scheduled_boundary_and_event_filter(async_client, configured):
    reset = int((configured + timedelta(seconds=60)).replace(tzinfo=UTC).timestamp())
    await snapshot(configured, 80, reset=reset)
    await snapshot(configured + timedelta(seconds=65), 0, reset=reset + 604800)
    assert json.loads((await deliveries())[0].payload)["kind"] == "scheduled"
    response = await async_client.put(PATH, json={"enabled": True, "kinds": ["scheduled"]})
    assert response.status_code == 200
    await snapshot(configured + timedelta(seconds=80), 90, reset=reset + 604800)
    await snapshot(configured + timedelta(seconds=100), 0, reset=reset + 604800)
    assert len(await deliveries()) == 1


async def test_worker_delivers_and_shutdown_releases_task(async_client, configured, monkeypatch):
    from unittest.mock import AsyncMock

    from app.modules.quota_webhook import scheduler
    from app.modules.quota_webhook.transport import DeliveryResult

    await async_client.post(PATH + "/test")
    sender = AsyncMock(return_value=DeliveryResult(204, None))
    monkeypatch.setattr(scheduler, "deliver", sender)
    worker = scheduler.QuotaWebhookWorker()
    assert await worker.run_once()
    assert not await worker.run_once()
    assert (await deliveries())[0].status == "delivered"
    sender.assert_awaited_once()
    await worker.start()
    await worker.stop()
    assert worker._task.done()


async def test_expired_lease_can_be_reclaimed_and_old_result_ignored(async_client, configured):
    await async_client.post(PATH + "/test")
    async with SessionLocal() as session:
        old = await claim(session)
        await session.execute(update(QuotaWebhookDelivery).values(lease_until=now_utc() - timedelta(seconds=1)))
        await session.commit()
    async with SessionLocal() as session:
        new = await claim(session)
        await settle(session, old, status=200, error=None, retryable=False)
    assert (await deliveries())[0].status == "sending"
    async with SessionLocal() as session:
        await settle(session, new, status=400, error="http_error", retryable=False)
    assert (await deliveries())[0].status == "failed"


async def test_missing_snapshot_breaks_baseline_and_rejects_stale_reappearance(configured):
    await snapshot(configured, 90)
    async with SessionLocal() as session:
        await UsageRepository(session).add_account_snapshot(
            "webhook-a", [], recorded_at=configured + timedelta(seconds=60)
        )
    await snapshot(configured + timedelta(seconds=30), 90)
    await snapshot(configured + timedelta(seconds=90), 0)
    assert await deliveries() == []


@pytest.mark.parametrize("field", ["chatgpt_user_id", "chatgpt_account_id", "plan_type"])
async def test_identity_changes_start_fresh_baseline(configured, field):
    from app.db.models import Account

    await snapshot(configured, 90)
    async with SessionLocal() as session:
        await session.execute(update(Account).where(Account.id == "webhook-a").values(**{field: "replacement"}))
        await session.commit()
    await snapshot(configured + timedelta(seconds=60), 0)
    assert await deliveries() == []


async def test_delivery_attempt_budget(async_client, configured):
    await async_client.post(PATH + "/test")
    for _ in range(4):
        async with SessionLocal() as session:
            delivery = await claim(session)
            assert delivery is not None
            await settle(session, delivery, status=429, error="http_error", retryable=True)
            await session.execute(update(QuotaWebhookDelivery).values(next_at=now_utc() - timedelta(seconds=1)))
            await session.commit()
    async with SessionLocal() as session:
        assert await claim(session) is None
    row = (await deliveries())[0]
    assert row.status == "failed" and row.attempts == 4


async def test_failed_snapshot_commit_rolls_back_notification_and_baseline(configured, monkeypatch):
    from unittest.mock import AsyncMock

    reset = int((configured + timedelta(days=3)).replace(tzinfo=UTC).timestamp())
    await snapshot(configured, 90, reset=reset)
    async with SessionLocal() as session:
        monkeypatch.setattr(session, "commit", AsyncMock(side_effect=RuntimeError("commit failed")))
        with pytest.raises(RuntimeError, match="commit failed"):
            await UsageRepository(session).add_account_snapshot(
                "webhook-a",
                [UsageWindowWrite(window="secondary", used_percent=0, window_minutes=10080, reset_at=reset)],
                recorded_at=configured + timedelta(seconds=60),
            )
    assert await deliveries() == []
    await snapshot(configured + timedelta(seconds=90), 0, reset=reset)
    assert len(await deliveries()) == 1
