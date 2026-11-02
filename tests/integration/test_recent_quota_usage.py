from __future__ import annotations

from datetime import UTC, timedelta

import pytest

from app.core.crypto import TokenEncryptor
from app.core.utils.time import naive_utc_to_epoch, utcnow
from app.db.models import Account, AccountStatus, AntigravityAccount, AntigravityQuotaHistory, ModelSource
from app.db.session import SessionLocal
from app.modules.accounts.repository import AccountsRepository
from app.modules.antigravity.schemas import AccountState as AntigravityState
from app.modules.antigravity.schemas import MetadataState, QuotaBucket
from app.modules.usage.repository import UsageRepository

pytestmark = pytest.mark.integration


def _account(account_id: str) -> Account:
    encryptor = TokenEncryptor()
    return Account(
        id=account_id,
        email=f"{account_id}@example.com",
        plan_type="plus",
        access_token_encrypted=encryptor.encrypt("access"),
        refresh_token_encrypted=encryptor.encrypt("refresh"),
        id_token_encrypted=encryptor.encrypt("id"),
        last_refresh=utcnow(),
        status=AccountStatus.ACTIVE,
        deactivation_reason=None,
    )


@pytest.mark.asyncio
async def test_dashboard_overview_reports_recent_codex_usage(async_client, db_setup):
    now = utcnow().replace(microsecond=0)
    five_hour_reset = naive_utc_to_epoch(now + timedelta(hours=3))
    weekly_reset = naive_utc_to_epoch(now + timedelta(days=4))
    fresh_reset = naive_utc_to_epoch(now + timedelta(hours=4, minutes=40))

    async with SessionLocal() as session:
        accounts = AccountsRepository(session)
        usage = UsageRepository(session)
        await accounts.upsert(_account("acc_busy"))
        await accounts.upsert(_account("acc_fresh"))
        for minutes_ago, used in ((70, 25.0), (30, 33.0), (1, 40.0)):
            await usage.add_entry(
                "acc_busy",
                used,
                window="primary",
                window_minutes=300,
                reset_at=five_hour_reset,
                recorded_at=now - timedelta(minutes=minutes_ago),
            )
        for minutes_ago, used in ((25 * 60, 30.0), (1, 36.0)):
            await usage.add_entry(
                "acc_busy",
                used,
                window="secondary",
                window_minutes=10080,
                reset_at=weekly_reset,
                recorded_at=now - timedelta(minutes=minutes_ago),
            )
        # The previous 5h window ended 20 minutes ago; the current one only knows its own 6%.
        await usage.add_entry(
            "acc_fresh",
            90.0,
            window="primary",
            window_minutes=300,
            reset_at=naive_utc_to_epoch(now - timedelta(minutes=20)),
            recorded_at=now - timedelta(hours=2),
        )
        await usage.add_entry(
            "acc_fresh",
            6.0,
            window="primary",
            window_minutes=300,
            reset_at=fresh_reset,
            recorded_at=now - timedelta(minutes=1),
        )
        await usage.add_entry(
            "acc_fresh",
            10.0,
            window="secondary",
            window_minutes=10080,
            reset_at=weekly_reset,
            recorded_at=now - timedelta(minutes=1),
        )

    response = await async_client.get("/api/dashboard/overview")
    assert response.status_code == 200
    accounts_by_id = {item["accountId"]: item["usage"] for item in response.json()["accounts"]}
    assert accounts_by_id["acc_busy"]["primaryRecentUsedPercent"] == pytest.approx(15.0)
    assert accounts_by_id["acc_busy"]["secondaryRecentUsedPercent"] == pytest.approx(6.0)
    assert accounts_by_id["acc_fresh"]["primaryRecentUsedPercent"] == pytest.approx(6.0)
    # No weekly reading from 24 hours ago: unknown, not zero.
    assert accounts_by_id["acc_fresh"]["secondaryRecentUsedPercent"] is None


@pytest.mark.asyncio
async def test_antigravity_accounts_report_recent_usage(async_client, db_setup):
    now = utcnow().replace(microsecond=0)
    aware_now = now.replace(tzinfo=UTC)
    state = AntigravityState(
        quota=[
            QuotaBucket(
                family="gemini", window="five_hour", remaining_fraction=0.6, resets_at=aware_now + timedelta(hours=3)
            ),
            QuotaBucket(
                family="gemini", window="weekly", remaining_fraction=0.64, resets_at=aware_now + timedelta(days=4)
            ),
            QuotaBucket(
                family="claude",
                window="five_hour",
                remaining_fraction=0.94,
                resets_at=aware_now + timedelta(hours=4, minutes=40),
            ),
        ],
        metadata={"quota": MetadataState(updated_at=aware_now)},
    )
    async with SessionLocal() as session:
        session.add(ModelSource(id="src_agy", name="Team Gemini", kind="antigravity", base_url="https://agy.invalid"))
        await session.flush()
        session.add(
            AntigravityAccount(
                source_id="src_agy",
                credentials_encrypted=b"sealed",
                google_subject="subject-agy",
                email="agy@example.com",
                session_id="1",
                expires_at=now + timedelta(hours=1),
                state_json=state.model_dump_json(),
            )
        )
        session.add_all(
            [
                AntigravityQuotaHistory(
                    source_id="src_agy",
                    observed_at=now - timedelta(minutes=70),
                    family="gemini",
                    window="five_hour",
                    used_percent=25.0,
                ),
                AntigravityQuotaHistory(
                    source_id="src_agy",
                    observed_at=now - timedelta(minutes=30),
                    family="gemini",
                    window="five_hour",
                    used_percent=33.0,
                ),
                AntigravityQuotaHistory(
                    source_id="src_agy",
                    observed_at=now - timedelta(hours=25),
                    family="gemini",
                    window="weekly",
                    used_percent=30.0,
                ),
                AntigravityQuotaHistory(
                    source_id="src_agy",
                    observed_at=now - timedelta(hours=2),
                    family="claude",
                    window="five_hour",
                    used_percent=90.0,
                ),
            ]
        )
        await session.commit()

    response = await async_client.get("/api/antigravity-accounts")
    assert response.status_code == 200, response.text
    [account] = response.json()["accounts"]
    windows = {(item["family"], item["window"]): item["recentUsedPercent"] for item in account["windows"]}
    assert windows[("gemini", "five_hour")] == pytest.approx(15.0)
    assert windows[("gemini", "weekly")] == pytest.approx(6.0)
    assert windows[("claude", "five_hour")] == pytest.approx(6.0)
