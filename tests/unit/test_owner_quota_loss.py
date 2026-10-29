from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.db.models import AccountStatus
from app.modules.proxy.owner_quota_loss import OwnerQuotaLoss, load_owner_quota_loss, owner_quota_loss_message

pytestmark = pytest.mark.unit

_RESETS_AT = 1793774149  # 2026-11-04 06:35:49 UTC


class _Repos:
    def __init__(self, get_by_id_fresh: AsyncMock) -> None:
        self.accounts = SimpleNamespace(get_by_id_fresh=get_by_id_fresh)

    async def __aenter__(self) -> _Repos:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False


def _factory(get_by_id_fresh: AsyncMock):
    return lambda: _Repos(get_by_id_fresh)


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [AccountStatus.RATE_LIMITED, AccountStatus.QUOTA_EXCEEDED])
async def test_spent_owner_reports_its_reset(status: AccountStatus) -> None:
    lookup = AsyncMock(return_value=SimpleNamespace(status=status, reset_at=_RESETS_AT))

    loss = await load_owner_quota_loss(_factory(lookup), "acc_owner")

    assert loss == OwnerQuotaLoss(resets_at=_RESETS_AT)
    lookup.assert_awaited_once_with("acc_owner")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status",
    [AccountStatus.ACTIVE, AccountStatus.PAUSED, AccountStatus.DEACTIVATED, AccountStatus.REAUTH_REQUIRED],
)
async def test_owner_lost_for_another_reason_is_not_a_quota_loss(status: AccountStatus) -> None:
    lookup = AsyncMock(return_value=SimpleNamespace(status=status, reset_at=_RESETS_AT))

    assert await load_owner_quota_loss(_factory(lookup), "acc_owner") is None


@pytest.mark.asyncio
async def test_missing_owner_is_not_a_quota_loss() -> None:
    assert await load_owner_quota_loss(_factory(AsyncMock(return_value=None)), "acc_owner") is None


@pytest.mark.asyncio
async def test_failed_owner_lookup_proves_nothing() -> None:
    lookup = AsyncMock(side_effect=RuntimeError("database unavailable"))

    assert await load_owner_quota_loss(_factory(lookup), "acc_owner") is None


def test_message_names_the_reset_and_the_way_out() -> None:
    assert owner_quota_loss_message(OwnerQuotaLoss(resets_at=_RESETS_AT)) == (
        "Previous response owner account reached its usage limit (resets 2026-11-04 06:35 UTC); "
        "retry without previous_response_id."
    )


def test_message_without_a_known_reset() -> None:
    assert owner_quota_loss_message(OwnerQuotaLoss(resets_at=None)) == (
        "Previous response owner account reached its usage limit; retry without previous_response_id."
    )
