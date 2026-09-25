from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.db.models import ClaudeVersionState
from app.db.session import SessionLocal
from app.modules.claude import version
from app.modules.claude.version import BASELINE_VERSION, ClaudeVersionService

pytestmark = pytest.mark.integration


def feed(monkeypatch, *, status=200, tag="v2.1.283", prerelease=False):
    calls = []

    @asynccontextmanager
    async def get(url, **kwargs):
        calls.append((url, kwargs))
        yield SimpleNamespace(status=status, headers={"ETag": '"release"'})

    @asynccontextmanager
    async def lease():
        yield SimpleNamespace(get=get)

    import json

    monkeypatch.setattr(version, "lease_model_source_session", lease)
    monkeypatch.setattr(
        version,
        "bounded_body",
        AsyncMock(
            return_value=json.dumps(
                {
                    "tag_name": tag,
                    "draft": False,
                    "prerelease": prerelease,
                }
            ).encode()
        ),
    )
    return calls


async def test_daily_refresh_unchanged_check_pin_and_restart(async_client, monkeypatch):
    calls = feed(monkeypatch)
    now = datetime(2026, 9, 25)
    async with SessionLocal() as session:
        service = ClaudeVersionService(session)
        snapshot = await service.snapshot()
        await service.refresh(now=now)
        assert (await service.snapshot()).version == "2.1.283"
        await service.refresh(now=now + timedelta(hours=23))
        assert len(calls) == 1
        await service.pin("2.1.280")
        assert snapshot.version == BASELINE_VERSION
    calls = feed(monkeypatch, status=304)
    async with SessionLocal() as session:
        service = ClaudeVersionService(session)
        await service.refresh(now=now + timedelta(days=1))
        state = await service.status()
        assert state.effective_version == "2.1.280"
        assert state.last_checked_at == now + timedelta(days=1)
        assert state.last_changed_at == now
        assert calls[0][1]["headers"]["If-None-Match"] == '"release"'
        await service.pin(None)
        assert (await service.snapshot()).version == "2.1.283"


@pytest.mark.parametrize(
    "status,tag,prerelease", [(503, "v2.1.283", False), (200, "latest", False), (200, "v2.1.283", True)]
)
async def test_failed_discovery_retains_version_with_retry(async_client, monkeypatch, status, tag, prerelease):
    calls = feed(monkeypatch, status=status, tag=tag, prerelease=prerelease)
    now = datetime(2026, 9, 25)
    async with SessionLocal() as session:
        service = ClaudeVersionService(session)
        await service.refresh(now=now)
        state = await service.status()
        assert state.effective_version == BASELINE_VERSION
        assert state.error and state.retry_at == now + timedelta(minutes=15)
        assert state.last_checked_at is None
        await service.refresh(now=now + timedelta(minutes=14))
        assert len(calls) == 1


async def test_stale_feed_does_not_downgrade(async_client, monkeypatch):
    feed(monkeypatch, tag="v2.1.200")
    async with SessionLocal() as session:
        service = ClaudeVersionService(session)
        await service.refresh(now=datetime(2026, 9, 25))
        assert (await service.snapshot()).version == BASELINE_VERSION
        row = await session.get(ClaudeVersionState, 1)
        assert row is not None
        assert row.last_changed_at is None


async def test_pin_api_validation_and_unpin(async_client):
    assert (await async_client.get("/api/claude-accounts/version")).json()["effectiveVersion"] == BASELINE_VERSION
    response = await async_client.patch("/api/claude-accounts/version", json={"version": "2.1.280"})
    assert response.status_code == 200
    assert response.json()["effectiveVersion"] == "2.1.280"
    assert (await async_client.patch("/api/claude-accounts/version", json={"version": "../bad"})).status_code == 400
    response = await async_client.patch("/api/claude-accounts/version", json={"version": None})
    assert response.json()["effectiveVersion"] == BASELINE_VERSION
