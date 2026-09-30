from datetime import timedelta

import pytest
import sqlalchemy as sa
from alembic import command

from app.core.usage.models import ReserveUsageSnapshot
from app.core.utils.time import naive_utc_to_epoch, utcnow
from app.db.migrate import _build_alembic_config, check_schema_drift, run_upgrade
from app.db.session import SessionLocal
from app.modules.accounts.repository import AccountsRepository
from app.modules.proxy.additional_model_limits import get_additional_model_limit
from app.modules.usage.repository import AdditionalUsageRepository
from tests.integration.test_additional_usage_flow import _make_account

pytestmark = pytest.mark.integration


def observation(*, age=0, allowed=True, windows=True):
    return ReserveUsageSnapshot.model_validate(
        {
            "observed_at": utcnow() - timedelta(seconds=age),
            "ordinary_allowed": False,
            "banner_type": "luna_reserve",
            "limit": {
                "limit_name": "gpt-reserve",
                "metered_feature": "base_model_inference",
                "rate_limit": {
                    "allowed": allowed,
                    "primary_window": {
                        "used_percent": 25,
                        "limit_window_seconds": 18000,
                        "reset_after_seconds": 3600,
                    }
                    if windows
                    else None,
                    "secondary_window": {
                        "used_percent": 60,
                        "limit_window_seconds": 604800,
                        "reset_at": 2000000000,
                    }
                    if windows
                    else None,
                },
            },
        }
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "age,allowed,windows,status",
    [
        (0, True, True, "available"),
        (0, False, True, "unavailable"),
        (0, True, False, "available"),
        (600, True, True, "unknown"),
    ],
)
async def test_account_api_displays_reserve_without_routing_grant(
    async_client, db_setup, age, allowed, windows, status
):
    account = _make_account("reserve-display", "reserve@test.example", "pro")
    snapshot = observation(age=age, allowed=allowed, windows=windows)
    async with SessionLocal() as session:
        await AccountsRepository(session).upsert(account)
        await AdditionalUsageRepository(session).record_reserve_usage(
            account.id, snapshot, expected_access_token_encrypted=account.access_token_encrypted
        )
    response = await async_client.get("/api/accounts")
    assert response.status_code == 200
    summaries = response.json()["accounts"]
    summary = next(item for item in summaries if item["accountId"] == account.id)
    quota = next(item for item in summary["additionalQuotas"] if item["limitName"] == "gpt-reserve")
    assert quota["displayLabel"] == "Luna Reserve"
    assert quota["availability"] == status
    assert quota["routingPolicy"] is None
    if windows and age == 0:
        assert quota["primaryWindow"]["usedPercent"] == 25
        assert quota["primaryWindow"]["windowMinutes"] == 300
        assert quota["secondaryWindow"]["usedPercent"] == 60
        assert quota["secondaryWindow"]["windowMinutes"] == 10080
        assert quota["primaryWindow"]["resetAt"] == naive_utc_to_epoch(snapshot.observed_at) + 3600
    else:
        assert quota["primaryWindow"] is None
        assert quota["secondaryWindow"] is None
    assert get_additional_model_limit("gpt-reserve") is None


@pytest.mark.asyncio
async def test_reserve_snapshot_rejects_old_credentials_and_late_observations(db_setup):
    account = _make_account("reserve-bound", "bound@test.example")
    async with SessionLocal() as session:
        accounts = AccountsRepository(session)
        await accounts.upsert(account)
        repo = AdditionalUsageRepository(session)
        snapshot = observation()
        await repo.record_reserve_usage(account.id, snapshot, expected_access_token_encrypted=b"wrong")
        current = await accounts.get_by_id_fresh(account.id)
        assert current is not None
        assert current.reserve_usage is None
        await repo.record_reserve_usage(
            account.id, snapshot, expected_access_token_encrypted=account.access_token_encrypted
        )
        await repo.record_reserve_usage(
            account.id,
            observation(age=60, allowed=False),
            expected_access_token_encrypted=account.access_token_encrypted,
        )
        current = await accounts.get_by_id_fresh(account.id)
        assert current is not None
        assert ReserveUsageSnapshot.model_validate(current.reserve_usage) == snapshot
        await accounts.upsert(_make_account(account.id, account.email))
        current = await accounts.get_by_id_fresh(account.id)
        assert current is not None
        assert current.reserve_usage is None


@pytest.mark.asyncio
async def test_absent_reserve_replaces_current_display_without_zero_usage(async_client, db_setup):
    account = _make_account("reserve-absent", "absent@test.example")
    async with SessionLocal() as session:
        await AccountsRepository(session).upsert(account)
        repo = AdditionalUsageRepository(session)
        await repo.record_reserve_usage(
            account.id, observation(age=60), expected_access_token_encrypted=account.access_token_encrypted
        )
        await repo.record_reserve_usage(
            account.id,
            ReserveUsageSnapshot(observed_at=utcnow()),
            expected_access_token_encrypted=account.access_token_encrypted,
        )
    summaries = (await async_client.get("/api/accounts")).json()["accounts"]
    summary = next(item for item in summaries if item["accountId"] == account.id)
    assert summary["additionalQuotas"] == []


def test_reserve_usage_migration_preserves_unknown_and_roundtrips(tmp_path):
    url = f"sqlite:///{tmp_path / 'reserve-usage.db'}"
    parent = "20260930_020000_account_reasoning_policy"
    run_upgrade(url, parent, bootstrap_legacy=False)
    engine = sa.create_engine(url)
    try:
        with engine.begin() as connection:
            connection.execute(
                sa.text(
                    "INSERT INTO accounts (id,email,plan_type,codex_installation_id,access_token_encrypted,"
                    "refresh_token_encrypted,id_token_encrypted,last_refresh,status) "
                    "VALUES ('historical','historical@test.example','pro','installation',X'01',X'02',X'03',"
                    "CURRENT_TIMESTAMP,'active')"
                )
            )
        run_upgrade(url, "head", bootstrap_legacy=False)
        with engine.connect() as connection:
            assert (
                connection.execute(sa.text("SELECT reserve_usage FROM accounts WHERE id='historical'")).scalar() is None
            )
        command.downgrade(_build_alembic_config(url), parent)
        run_upgrade(url, "head", bootstrap_legacy=False)
        assert check_schema_drift(url) == ()
    finally:
        engine.dispose()
