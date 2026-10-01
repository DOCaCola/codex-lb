import math
from datetime import UTC, datetime, timedelta

import pytest

from app.db.models import ClaudeAccount, ClaudeCooldown
from app.db.session import SessionLocal
from app.modules.claude.failover import Refusal, record_refusals
from app.modules.claude.routing import ClaudePoolUnavailable
from app.modules.claude.schemas import AccountState, QuotaWindow, UsageSnapshot
from tests.integration.test_claude_routing import MODEL, choose, key
from tests.integration.test_claude_routing import pool as pool

pytestmark = pytest.mark.integration


async def exhaust(source, deadline):
    async with SessionLocal() as session:
        row = await session.get(ClaudeAccount, source)
        state = AccountState.model_validate_json(row.state_json)
        state.usage = UsageSnapshot(five_hour=QuotaWindow(utilization=100, resets_at=deadline))
        state.usage_updated_at = datetime.now(UTC)
        state.usage_requested_at = state.usage_updated_at
        row.state_json = state.model_dump_json()
        await session.commit()


async def test_latest_per_account_earliest_across_pool_and_owner(pool):
    now = datetime.now(UTC)
    await exhaust(pool[0], now + timedelta(hours=2))
    await exhaust(pool[1], now + timedelta(hours=3))
    await record_refusals(
        pool[0],
        MODEL,
        (Refusal("model", now + timedelta(hours=5), "reset", "seven_day_overage_included"),),
        requested_at=now,
    )
    with pytest.raises(ClaudePoolUnavailable) as caught:
        await choose(now=now)
    assert caught.value.status_code == 429
    assert caught.value.retry_at == now + timedelta(hours=3)
    with pytest.raises(ClaudePoolUnavailable) as caught:
        await choose(owner_source_id=pool[0], now=now)
    assert caught.value.status_code == 429
    assert caught.value.code == "previous_response_owner_unavailable"
    assert caught.value.retry_at == now + timedelta(hours=5)
    assert "five_hour" in str(caught.value)
    assert "seven_day_overage_included" in str(caught.value)
    assert caught.value.error_detail["resets_at"] == math.ceil((now + timedelta(hours=5)).timestamp())
    scoped = key(source_assignment_scope_enabled=True, assigned_source_ids=[pool[0]])
    with pytest.raises(ClaudePoolUnavailable) as caught:
        await choose(api_key=scoped, now=now)
    assert caught.value.retry_at == now + timedelta(hours=5)


async def test_unknown_deadline_and_mixed_states(pool):
    await exhaust(pool[0], None)
    await exhaust(pool[1], None)
    with pytest.raises(ClaudePoolUnavailable) as caught:
        await choose()
    assert caught.value.status_code == 429
    assert caught.value.response_headers == {}
    assert "resets_at" not in caught.value.error_detail
    assert "resets_in_seconds" not in caught.value.error_detail
    with pytest.raises(ClaudePoolUnavailable) as owner:
        await choose(owner_source_id=pool[0])
    assert owner.value.status_code == 429
    assert owner.value.code == "previous_response_owner_unavailable"
    assert owner.value.response_headers == {}
    assert "resets_at" not in owner.value.error_detail
    async with SessionLocal() as session:
        row = await session.get(ClaudeAccount, pool[1])
        row.credential_status = "reauth_required"
        await session.commit()
    with pytest.raises(ClaudePoolUnavailable) as caught:
        await choose()
    assert caught.value.status_code == 503
    assert caught.value.response_headers == {}


async def test_backoff_does_not_hide_later_quota_and_paused_deadlines_are_ignored(pool, async_client):
    now = datetime.now(UTC)
    await exhaust(pool[0], now + timedelta(hours=4))
    await exhaust(pool[1], now + timedelta(hours=1))
    async with SessionLocal() as session:
        row = await session.get(ClaudeAccount, pool[0])
        row.retry_at = (now + timedelta(minutes=5)).replace(tzinfo=None)
        await session.commit()
    await async_client.patch(f"/api/claude-accounts/{pool[1]}", json={"isEnabled": False})
    with pytest.raises(ClaudePoolUnavailable) as caught:
        await choose(now=now)
    assert caught.value.status_code == 503
    assert caught.value.retry_at == now + timedelta(hours=4)


@pytest.mark.parametrize(
    "path",
    [
        "/v1/messages",
        "/v1/messages/count_tokens",
        "/v1/responses",
        "/backend-api/codex/responses",
    ],
)
async def test_pool_error_at_http_boundary(async_client, pool, path):
    now = datetime.now(UTC)
    for source in pool:
        await exhaust(source, now + timedelta(minutes=5))
    body = {"model": MODEL}
    if "/messages" in path:
        body.update(messages=[{"role": "user", "content": "Hello"}], max_tokens=100)
    else:
        body.update(input="Hello")
    response = await async_client.post(path, json=body)
    assert response.status_code == 429, response.text
    assert response.json()["error"]["code"] == "claude_pool_rate_limited"
    native = "/messages" in path
    assert response.json()["error"]["type"] == ("rate_limit_error" if native else "usage_limit_reached")
    assert "plan_type" not in response.json()["error"]
    assert 290 <= int(response.headers["retry-after"]) <= 300
    assert response.json()["error"]["resets_at"] == math.ceil((now + timedelta(minutes=5)).timestamp())
    assert 290 <= response.json()["error"]["resets_in_seconds"] <= 300
    assert "five_hour" in response.json()["error"]["message"]


@pytest.mark.parametrize("barrier", ["paused", "credentials", "refreshing", "refresh_backoff", "unknown"])
async def test_non_quota_owner_keeps_503_even_with_observed_exhaustion(pool, barrier):
    now = datetime.now(UTC)
    await exhaust(pool[0], now + timedelta(hours=2))
    async with SessionLocal() as session:
        row = await session.get(ClaudeAccount, pool[0])
        if barrier == "paused":
            row.source.is_enabled = False
        elif barrier == "credentials":
            row.credential_status = "reauth_required"
        elif barrier == "refreshing":
            row.refresh_intent = "owned-refresh"
        elif barrier == "refresh_backoff":
            row.retry_at = (now + timedelta(minutes=5)).replace(tzinfo=None)
        else:
            session.add(
                ClaudeCooldown(source_id=pool[0], model="*", until=(now + timedelta(hours=3)).replace(tzinfo=None))
            )
        await session.commit()
    assert await choose(now=now) == pool[1]
    with pytest.raises(ClaudePoolUnavailable) as caught:
        await choose(owner_source_id=pool[0], now=now)
    assert caught.value.status_code == 503
    assert caught.value.error_type == "server_error"
    assert caught.value.code == "previous_response_owner_unavailable"


async def test_excluded_candidate_does_not_turn_mixed_pool_into_quota_only(pool):
    await exhaust(pool[0], datetime.now(UTC) + timedelta(hours=2))
    with pytest.raises(ClaudePoolUnavailable) as caught:
        await choose(excluded_source_ids=frozenset({pool[1]}))
    assert caught.value.status_code == 503
    assert "excluded: 1" in str(caught.value)


@pytest.mark.parametrize("known_weekly_reset", [False, True])
async def test_owner_retry_requires_every_exhausted_window_to_recover(pool, known_weekly_reset):
    now = datetime.now(UTC)
    weekly_reset = now + timedelta(hours=4) if known_weekly_reset else None
    async with SessionLocal() as session:
        row = await session.get(ClaudeAccount, pool[0])
        state = AccountState.model_validate_json(row.state_json)
        state.usage = UsageSnapshot(
            five_hour=QuotaWindow(utilization=100, resets_at=now + timedelta(hours=2)),
            seven_day=QuotaWindow(utilization=100, resets_at=weekly_reset),
        )
        state.usage_updated_at = state.usage_requested_at = now
        row.state_json = state.model_dump_json()
        await session.commit()
    with pytest.raises(ClaudePoolUnavailable) as caught:
        await choose(owner_source_id=pool[0], now=now)
    error = caught.value
    assert error.status_code == 429
    assert error.retry_at == weekly_reset
    assert "five_hour, seven_day" in str(error)
    if weekly_reset is None:
        assert "resets_at" not in error.error_detail
        assert error.response_headers == {}
    else:
        assert error.error_detail["resets_at"] == math.ceil(weekly_reset.timestamp())
        # Passing both deadlines permits the same owner, without moving history.
        assert await choose(owner_source_id=pool[0], now=weekly_reset + timedelta(seconds=1)) == pool[0]
