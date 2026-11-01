import json
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.db.models import ClaudeClientBuild, ClaudeVersionState
from app.db.session import SessionLocal
from app.modules.claude import version
from app.modules.claude.credentials import ClaudeError
from app.modules.claude.profile import ClientBuild
from app.modules.claude.version import BASELINE_VERSION, REVIEWED_BUILDS, ClaudeVersionService, PackageDist

pytestmark = pytest.mark.integration

DIST = PackageDist(
    tarball="https://registry.npmjs.org/@anthropic-ai/claude-code-linux-x64/-/claude-code-linux-x64-2.1.320.tgz",
    integrity="sha512-" + "A" * 86 + "==",
)


def feed(monkeypatch, *, status=200, tag="v2.1.320", prerelease=False):
    calls = []

    @asynccontextmanager
    async def get(url, **kwargs):
        calls.append((url, kwargs))
        yield SimpleNamespace(status=status, headers={"ETag": '"release"'})

    @asynccontextmanager
    async def lease():
        yield SimpleNamespace(get=get)

    monkeypatch.setattr(version, "lease_model_source_session", lease)
    monkeypatch.setattr(
        version,
        "bounded_body",
        AsyncMock(return_value=json.dumps({"tag_name": tag, "draft": False, "prerelease": prerelease}).encode()),
    )
    return calls


def build_check(monkeypatch, result=("0.130.0", "v26.13.0")):
    package = AsyncMock(return_value=DIST)
    identity = AsyncMock(side_effect=[result] if not isinstance(result, Exception) else result)
    monkeypatch.setattr(version, "_package_dist", package)
    monkeypatch.setattr(version, "_verified_runtime_identity", identity)
    return package, identity


async def test_new_release_is_adopted_only_as_a_verified_build(async_client, monkeypatch):
    calls = feed(monkeypatch)
    package, identity = build_check(monkeypatch)
    now = datetime(2026, 11, 1)
    async with SessionLocal() as session:
        service = ClaudeVersionService(session)
        assert await service.snapshot() == REVIEWED_BUILDS[BASELINE_VERSION]
        await service.refresh(now=now)
        assert await service.snapshot() == ClientBuild("2.1.320", "0.130.0", "v26.13.0")
        package.assert_awaited_once_with("2.1.320")
        identity.assert_awaited_once_with(DIST)
        stored = await session.get(ClaudeClientBuild, "2.1.320")
        assert stored is not None and stored.integrity == DIST.integrity
        await service.refresh(now=now + timedelta(hours=23))
        assert len(calls) == 1
        assert await service.pin("2.1.282") == REVIEWED_BUILDS["2.1.282"]
    calls = feed(monkeypatch, status=304)
    async with SessionLocal() as session:
        service = ClaudeVersionService(session)
        await service.refresh(now=now + timedelta(days=1))
        state = await service.status()
        assert state.effective.version == "2.1.282"
        assert state.last_checked_at == now + timedelta(days=1)
        assert state.last_changed_at == now
        assert calls[0][1]["headers"]["If-None-Match"] == '"release"'
        assert [build.version for build in state.builds] == ["2.1.320", "2.1.316", "2.1.282"]
        await service.pin(None)
        assert (await service.snapshot()).version == "2.1.320"
        assert identity.await_count == 1


async def test_reviewed_release_needs_no_download(async_client, monkeypatch):
    feed(monkeypatch, tag="v" + BASELINE_VERSION)
    package, _ = build_check(monkeypatch)
    async with SessionLocal() as session:
        service = ClaudeVersionService(session)
        await service.refresh(now=datetime(2026, 11, 1))
        assert (await service.status()).last_checked_at == datetime(2026, 11, 1)
    package.assert_not_awaited()


async def test_failed_verification_keeps_the_verified_version_and_retries(async_client, monkeypatch):
    feed(monkeypatch)
    build_check(monkeypatch, ClaudeError("Claude Code binary has no unambiguous SDK and runtime version"))
    now = datetime(2026, 11, 1)
    async with SessionLocal() as session:
        service = ClaudeVersionService(session)
        await service.refresh(now=now)
        state = await service.status()
        assert state.effective.version == BASELINE_VERSION
        assert state.error is not None and state.error.startswith("Claude Code binary has no unambiguous")
        assert state.retry_at == now + version.RETRY_INTERVAL
        assert state.last_checked_at is None
        row = await session.get(ClaudeVersionState, 1)
        assert row is not None and row.etag is None
    calls = feed(monkeypatch)
    build_check(monkeypatch)
    async with SessionLocal() as session:
        service = ClaudeVersionService(session)
        await service.refresh(now=now + version.RETRY_INTERVAL)
        assert (await service.snapshot()).version == "2.1.320"
    assert "If-None-Match" not in calls[0][1]["headers"]


@pytest.mark.parametrize(
    "status,tag,prerelease", [(503, "v2.1.320", False), (200, "latest", False), (200, "v2.1.320", True)]
)
async def test_failed_discovery_retains_version_with_retry(async_client, monkeypatch, status, tag, prerelease):
    calls = feed(monkeypatch, status=status, tag=tag, prerelease=prerelease)
    now = datetime(2026, 11, 1)
    async with SessionLocal() as session:
        service = ClaudeVersionService(session)
        await service.refresh(now=now)
        state = await service.status()
        assert state.effective.version == BASELINE_VERSION
        assert state.error and state.retry_at == now + version.RETRY_INTERVAL
        assert state.last_checked_at is None
        await service.refresh(now=now + timedelta(minutes=14))
        assert len(calls) == 1


async def test_stale_feed_does_not_downgrade(async_client, monkeypatch):
    feed(monkeypatch, tag="v2.1.200")
    package, _ = build_check(monkeypatch)
    async with SessionLocal() as session:
        service = ClaudeVersionService(session)
        await service.refresh(now=datetime(2026, 11, 1))
        assert (await service.snapshot()).version == BASELINE_VERSION
        row = await session.get(ClaudeVersionState, 1)
        assert row is not None
        assert row.last_changed_at is None
    package.assert_not_awaited()


async def test_pin_api_accepts_only_verified_builds(async_client):
    response = await async_client.get("/api/claude-accounts/version")
    assert response.json()["effective"] == {
        "version": BASELINE_VERSION,
        "sdkVersion": "0.128.0",
        "runtimeVersion": "v26.12.1",
        "verifiedAt": None,
    }
    response = await async_client.patch("/api/claude-accounts/version", json={"version": "2.1.282"})
    assert response.status_code == 200
    assert response.json()["effective"]["sdkVersion"] == "0.112.1"
    assert (await async_client.patch("/api/claude-accounts/version", json={"version": "2.1.280"})).status_code == 400
    assert (await async_client.patch("/api/claude-accounts/version", json={"version": "../bad"})).status_code == 400
    response = await async_client.patch("/api/claude-accounts/version", json={"version": None})
    assert response.json()["effective"]["version"] == BASELINE_VERSION
