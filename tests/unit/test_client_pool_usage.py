from __future__ import annotations

import pytest

from app.core.usage import summarize_client_pool
from app.core.usage.types import UsageWindowRow
from app.core.utils.time import utcnow
from app.db.models import Account, AccountStatus

pytestmark = pytest.mark.unit


def _account(account_id: str, plan_type: str) -> Account:
    return Account(
        id=account_id,
        email=f"{account_id}@example.com",
        plan_type=plan_type,
        access_token_encrypted=b"access",
        refresh_token_encrypted=b"refresh",
        id_token_encrypted=b"id",
        last_refresh=utcnow(),
        status=AccountStatus.ACTIVE,
    )


def _row(account_id: str, used_percent: float, reset_at: int, window_minutes: int) -> UsageWindowRow:
    return UsageWindowRow(
        account_id=account_id,
        used_percent=used_percent,
        reset_at=reset_at,
        window_minutes=window_minutes,
    )


def test_accounts_without_a_5h_window_do_not_make_the_pool_5h_limited() -> None:
    accounts = {
        "alpha": _account("alpha", "pro"),
        "beta": _account("beta", "pro"),
        "plus": _account("plus", "plus"),
    }

    pool = summarize_client_pool(
        primary_rows=[_row("plus", 100.0, 1_000, 300)],
        secondary_rows=[
            _row("alpha", 43.0, 9_000, 10_080),
            _row("beta", 9.0, 8_000, 10_080),
            _row("plus", 56.0, 7_000, 10_080),
        ],
        monthly_rows=[],
        account_map=accounts,
        now_epoch=0,
    )

    assert pool.primary is not None
    # Plus is exhausted; both Pro accounts have no 5h limit.
    assert pool.primary.used_percent == pytest.approx(225.0 / (1500.0 + 1500.0 + 225.0) * 100.0)
    assert pool.primary.reset_at == 1_000
    assert pool.primary.window_minutes == 300
    assert pool.monthly is None


def test_an_exhausted_account_counts_as_fully_used_in_every_window() -> None:
    accounts = {"pro": _account("pro", "pro"), "plus": _account("plus", "plus")}

    pool = summarize_client_pool(
        primary_rows=[_row("plus", 10.0, 1_000, 300)],
        secondary_rows=[_row("pro", 100.0, 9_000, 10_080), _row("plus", 20.0, 7_000, 10_080)],
        monthly_rows=[],
        account_map=accounts,
        now_epoch=0,
    )

    assert pool.primary is not None
    assert pool.primary.used_percent == pytest.approx((1500.0 + 22.5) / (1500.0 + 225.0) * 100.0)
    # The Pro account has no 5h usage of its own, so its weekly reset does not set the 5h reset.
    assert pool.primary.reset_at == 1_000


def test_idle_accounts_do_not_set_the_reset_time() -> None:
    accounts = {"idle": _account("idle", "plus"), "busy": _account("busy", "plus")}

    pool = summarize_client_pool(
        primary_rows=[_row("idle", 0.0, 500, 300), _row("busy", 30.0, 2_000, 300)],
        secondary_rows=[],
        monthly_rows=[],
        account_map=accounts,
        now_epoch=0,
    )

    assert pool.primary is not None
    assert pool.primary.reset_at == 2_000
    assert pool.secondary is None


def test_an_idle_pool_reports_no_reset() -> None:
    pool = summarize_client_pool(
        primary_rows=[_row("plus", 0.0, 500, 300)],
        secondary_rows=[],
        monthly_rows=[],
        account_map={"plus": _account("plus", "plus")},
        now_epoch=0,
    )

    assert pool.primary is not None
    assert pool.primary.used_percent == 0.0
    assert pool.primary.reset_at is None


def test_an_elapsed_sample_no_longer_reports_its_window() -> None:
    accounts = {"stale": _account("stale", "plus"), "pro": _account("pro", "pro")}

    pool = summarize_client_pool(
        primary_rows=[_row("stale", 100.0, 500, 300)],
        secondary_rows=[_row("stale", 40.0, 9_000, 10_080), _row("pro", 10.0, 9_000, 10_080)],
        monthly_rows=[],
        account_map=accounts,
        now_epoch=1_000,
    )

    assert pool.primary is None
    assert pool.secondary is not None
    # The elapsed 100% sample does not mark the account exhausted.
    assert pool.secondary.used_percent == pytest.approx((7560.0 * 0.4 + 50400.0 * 0.1) / (7560.0 + 50400.0) * 100.0)


def test_accounts_weigh_equally_when_no_plan_capacity_is_known() -> None:
    accounts = {"metered": _account("metered", "plus"), "unmetered": _account("unmetered", "plus")}

    pool = summarize_client_pool(
        primary_rows=[],
        secondary_rows=[_row("unmetered", 0.0, 9_000, 10_080)],
        monthly_rows=[_row("metered", 42.0, 9_000, 43_200)],
        account_map=accounts,
        now_epoch=0,
    )

    assert pool.monthly is not None
    assert pool.monthly.used_percent == pytest.approx(21.0)
    assert pool.monthly.reset_at == 9_000
