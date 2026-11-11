from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from app.db.models import AccountStatus
from app.modules.accounts.service import AccountNotRefreshableError, AccountUsageRefreshFailedError
from app.modules.usage.updater import AccountRefreshResult
from tests.unit.test_accounts_service_probe import _ACCOUNT_ID, _build_service, _make_account

pytestmark = pytest.mark.unit


@pytest.fixture
def selection_cache(monkeypatch):
    cache = SimpleNamespace(invalidate=Mock())
    monkeypatch.setattr("app.modules.accounts.service.get_account_selection_cache", lambda: cache)
    return cache


def _forbid_probe(service, monkeypatch):
    async def _probe(**kwargs):
        raise AssertionError("refresh must not send a model request")

    monkeypatch.setattr(service, "_send_probe_request", _probe)


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [AccountStatus.ACTIVE, AccountStatus.PAUSED, AccountStatus.RATE_LIMITED])
async def test_refresh_fetches_usage_without_a_model_request(monkeypatch, selection_cache, status):
    account = _make_account(status=status)
    service = _build_service(account)
    _forbid_probe(service, monkeypatch)

    result = await service.refresh_account(_ACCOUNT_ID)

    assert result is not None
    assert result.status == "refreshed"
    assert service._usage_updater is not None
    force_refresh = service._usage_updater.force_refresh_result
    assert isinstance(force_refresh, AsyncMock)
    force_refresh.assert_awaited_once_with(account)
    selection_cache.invalidate.assert_called_once()


@pytest.mark.asyncio
async def test_refresh_returns_none_for_missing_account():
    assert await _build_service(None).refresh_account("missing") is None


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [AccountStatus.REAUTH_REQUIRED, AccountStatus.DEACTIVATED])
async def test_refresh_rejects_accounts_without_usable_credentials(status):
    service = _build_service(_make_account(status=status))
    with pytest.raises(AccountNotRefreshableError):
        await service.refresh_account(_ACCOUNT_ID)
    assert service._usage_updater is not None
    force_refresh = service._usage_updater.force_refresh_result
    assert isinstance(force_refresh, AsyncMock)
    force_refresh.assert_not_awaited()


@pytest.mark.asyncio
async def test_refresh_reports_a_failed_fetch_after_invalidating_cached_credentials(selection_cache):
    service = _build_service(_make_account())
    assert service._usage_updater is not None
    force_refresh = service._usage_updater.force_refresh_result
    assert isinstance(force_refresh, AsyncMock)
    force_refresh.return_value = AccountRefreshResult(usage_written=False, fetch_succeeded=False)

    with pytest.raises(AccountUsageRefreshFailedError):
        await service.refresh_account(_ACCOUNT_ID)
    selection_cache.invalidate.assert_called_once()
