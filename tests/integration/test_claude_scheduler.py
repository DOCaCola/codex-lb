from unittest.mock import AsyncMock

import pytest

from app.modules.claude.scheduler import ClaudeRefreshScheduler
from app.modules.claude.service import ClaudeService
from app.modules.claude.version import ClaudeVersionService
from tests.integration import test_claude_accounts as account_fixtures
from tests.integration.test_claude_accounts import import_body

profile_stub = account_fixtures.profile_stub

pytestmark = pytest.mark.integration


async def test_scheduler_no_network_without_enabled_accounts(async_client, monkeypatch):
    version = AsyncMock()
    metadata = AsyncMock()
    monkeypatch.setattr(ClaudeVersionService, "refresh", version)
    monkeypatch.setattr(ClaudeService, "refresh", metadata)
    scheduler = ClaudeRefreshScheduler()
    await scheduler.refresh_once()
    version.assert_not_awaited()
    source_id = (await async_client.post("/api/claude-accounts/import", json=import_body())).json()["id"]
    await async_client.patch(f"/api/claude-accounts/{source_id}", json={"isEnabled": False})
    await scheduler.refresh_once()
    version.assert_not_awaited()
    metadata.assert_not_awaited()


async def test_scheduler_isolates_account_failure_and_sessions(async_client, monkeypatch):
    version = AsyncMock()
    seen = []

    async def refresh(self, source_id, *, catalog):
        seen.append((source_id, self.repository.session, catalog))
        if len(seen) == 1:
            raise RuntimeError("credential-bearing exception must not be logged")

    monkeypatch.setattr(ClaudeVersionService, "refresh", version)
    monkeypatch.setattr(ClaudeService, "refresh", refresh)
    ids = [
        (await async_client.post("/api/claude-accounts/import", json=import_body(refresh=secret))).json()["id"]
        for secret in ("first", "second")
    ]
    await ClaudeRefreshScheduler().refresh_once()
    version.assert_awaited_once()
    assert {entry[0] for entry in seen} == set(ids)
    assert seen[0][1] is not seen[1][1]
    assert all(entry[2] for entry in seen)
