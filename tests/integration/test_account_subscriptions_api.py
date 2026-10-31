from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.core.crypto import TokenEncryptor
from app.db.models import Account, AccountStatus, ModelSource
from app.db.session import SessionLocal

pytestmark = pytest.mark.integration

_CREATED = datetime(2026, 6, 1, tzinfo=timezone.utc).replace(tzinfo=None)


def _account(account_id: str, *, delete_requested: bool = False) -> Account:
    encryptor = TokenEncryptor()
    return Account(
        id=account_id,
        email=f"{account_id}@example.com",
        plan_type="plus",
        access_token_encrypted=encryptor.encrypt("access"),
        refresh_token_encrypted=encryptor.encrypt("refresh"),
        id_token_encrypted=encryptor.encrypt("id"),
        last_refresh=_CREATED,
        created_at=_CREATED,
        status=AccountStatus.ACTIVE,
        deactivation_reason=None,
        delete_requested_at=_CREATED if delete_requested else None,
    )


def _source(source_id: str, kind: str) -> ModelSource:
    return ModelSource(id=source_id, name=source_id, kind=kind, base_url="https://source.invalid", created_at=_CREATED)


async def _seed() -> None:
    async with SessionLocal() as session:
        session.add(_account("acc_live"))
        session.add(_account("acc_gone", delete_requested=True))
        session.add(_source("src_claude", "claude"))
        session.add(_source("src_antigravity", "antigravity"))
        session.add(_source("src_openrouter", "openrouter"))
        await session.commit()


def _by_identity(payload: dict) -> dict[str, str]:
    return {entry["accountId"] or entry["modelSourceId"]: entry["endsAt"] for entry in payload["ends"]}


@pytest.mark.asyncio
async def test_end_dates_are_stored_in_utc_and_cleared(async_client, db_setup):
    await _seed()

    assert (await async_client.get("/api/account-subscriptions")).json() == {"ends": []}

    saved = await async_client.put(
        "/api/account-subscriptions/accounts/acc_live", json={"endsAt": "2026-11-15T18:00:00+01:00"}
    )
    assert saved.status_code == 200
    assert _by_identity(saved.json()) == {"acc_live": "2026-11-15T17:00:00Z"}

    claude = await async_client.put(
        "/api/account-subscriptions/model-sources/src_claude", json={"endsAt": "2026-12-01T00:00:00Z"}
    )
    antigravity = await async_client.put(
        "/api/account-subscriptions/model-sources/src_antigravity", json={"endsAt": "2026-12-02T00:00:00Z"}
    )
    assert claude.status_code == 200
    assert _by_identity(antigravity.json()) == {
        "acc_live": "2026-11-15T17:00:00Z",
        "src_claude": "2026-12-01T00:00:00Z",
        "src_antigravity": "2026-12-02T00:00:00Z",
    }

    await async_client.put("/api/account-subscriptions/accounts/acc_live", json={"endsAt": None})
    await async_client.put("/api/account-subscriptions/model-sources/src_claude", json={"endsAt": None})
    cleared = await async_client.put("/api/account-subscriptions/model-sources/src_antigravity", json={"endsAt": None})
    assert cleared.json() == {"ends": []}


@pytest.mark.asyncio
async def test_rejects_unknown_inapplicable_and_naive_targets(async_client, db_setup):
    await _seed()
    end = {"endsAt": "2026-11-15T18:00:00Z"}

    gone = await async_client.put("/api/account-subscriptions/accounts/acc_gone", json=end)
    assert gone.status_code == 404
    assert gone.json()["error"]["code"] == "account_not_found"
    missing = await async_client.put("/api/account-subscriptions/model-sources/missing", json=end)
    assert missing.status_code == 404
    openrouter = await async_client.put("/api/account-subscriptions/model-sources/src_openrouter", json=end)
    assert openrouter.status_code == 400
    assert openrouter.json()["error"]["code"] == "subscription_end_not_applicable"
    naive = await async_client.put(
        "/api/account-subscriptions/accounts/acc_live", json={"endsAt": "2026-11-15T18:00:00"}
    )
    assert naive.status_code in {400, 422}
