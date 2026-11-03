"""The served Codex catalog follows pool membership, not account availability.

Codex renders the catalog into its subagent tool description, so any catalog
change rewrites the cached prompt prefix of every client.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

import pytest
from sqlalchemy import select, update

import app.core.cache.invalidation as invalidation_module
import app.core.openai.model_refresh_scheduler as scheduler_module
from app.core.cache.invalidation import CacheInvalidationPoller
from app.core.crypto import TokenEncryptor
from app.core.openai.model_registry import ReasoningLevel, UpstreamModel
from app.core.utils.time import utcnow
from app.db.models import Account, AccountStatus, ModelRegistrySnapshotRecord
from app.db.session import SessionLocal

pytestmark = pytest.mark.integration

_CATALOGS = {
    "acc-pro": ("pro", ("gpt-stable-shared", "gpt-stable-pro")),
    "acc-plus": ("plus", ("gpt-stable-shared", "gpt-stable-plus")),
}


def _model(slug: str) -> UpstreamModel:
    return UpstreamModel(
        slug=slug,
        display_name=slug,
        description=f"Test model {slug}",
        context_window=272000,
        input_modalities=("text",),
        supported_reasoning_levels=(ReasoningLevel(effort="medium", description="balanced"),),
        default_reasoning_level="medium",
        supports_reasoning_summaries=False,
        support_verbosity=False,
        default_verbosity=None,
        prefer_websockets=False,
        supports_parallel_tool_calls=True,
        supported_in_api=True,
        minimal_client_version=None,
        priority=1,
        available_in_plans=frozenset({"plus", "pro"}),
        raw={"shell_type": "shell_command", "visibility": "list", "availability_nux": None},
    )


class _Leader:
    async def run_if_leader(self, fn: Callable[[], Awaitable[object]]) -> object:
        return await fn()


async def _set_status(account_id: str, status: AccountStatus) -> None:
    async with SessionLocal() as session:
        await session.execute(update(Account).where(Account.id == account_id).values(status=status))
        await session.commit()


async def _snapshot_hash() -> str:
    async with SessionLocal() as session:
        row = await session.scalar(select(ModelRegistrySnapshotRecord).where(ModelRegistrySnapshotRecord.id == 1))
    assert row is not None
    return row.content_hash


@pytest.mark.asyncio
async def test_temporary_account_conditions_keep_the_served_catalog_identical(async_client, monkeypatch) -> None:
    encryptor = TokenEncryptor()
    async with SessionLocal() as session:
        for account_id, (plan_type, _slugs) in _CATALOGS.items():
            session.add(
                Account(
                    id=account_id,
                    email=f"{account_id}@example.com",
                    plan_type=plan_type,
                    access_token_encrypted=encryptor.encrypt("access"),
                    refresh_token_encrypted=encryptor.encrypt("refresh"),
                    id_token_encrypted=encryptor.encrypt("id"),
                    last_refresh=utcnow(),
                    status=AccountStatus.ACTIVE,
                )
            )
        await session.commit()

    fetched: list[str] = []

    async def _fetch(candidates, encryptor, accounts_repo=None):
        account_models = {}
        for account in candidates:
            fetched.append(account.id)
            plan_type, slugs = _CATALOGS[account.id]
            account_models[account.id] = (plan_type, [_model(slug) for slug in slugs])
        merged = {model.slug: model for _plan, models in account_models.values() for model in models}
        return scheduler_module._FetchResult(models=list(merged.values()), account_models=account_models)

    monkeypatch.setattr(scheduler_module, "_get_leader_election", lambda: _Leader())
    monkeypatch.setattr(scheduler_module, "_fetch_with_failover", _fetch)
    monkeypatch.setattr(invalidation_module, "_poller", CacheInvalidationPoller(SessionLocal))
    scheduler = scheduler_module.ModelRefreshScheduler(interval_seconds=300, enabled=True)

    async def _refresh_and_serve() -> tuple[bytes, str]:
        fetched.clear()
        await scheduler._refresh_once()
        response = await async_client.get("/backend-api/codex/models")
        assert response.status_code == 200
        return response.content, await _snapshot_hash()

    baseline = await _refresh_and_serve()
    assert b"gpt-stable-plus" in baseline[0]

    for status, plus_fetched in (
        (AccountStatus.QUOTA_EXCEEDED, True),
        (AccountStatus.RATE_LIMITED, True),
        (AccountStatus.PAUSED, False),
        (AccountStatus.REAUTH_REQUIRED, False),
        (AccountStatus.ACTIVE, True),
    ):
        await _set_status("acc-plus", status)
        assert await _refresh_and_serve() == baseline, status
        assert ("acc-plus" in fetched) is plus_fetched, status

    await _set_status("acc-plus", AccountStatus.DEACTIVATED)
    content, _hash = await _refresh_and_serve()
    assert b"gpt-stable-plus" not in content
    assert b"gpt-stable-shared" in content
