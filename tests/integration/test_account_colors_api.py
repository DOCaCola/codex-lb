from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.core.crypto import TokenEncryptor
from app.db.models import Account, AccountStatus, ModelSource
from app.db.session import SessionLocal

pytestmark = pytest.mark.integration

_CREATED = datetime(2026, 6, 1, tzinfo=timezone.utc).replace(tzinfo=None)


def _account(account_id: str, created_at: datetime, *, delete_requested: bool = False) -> Account:
    encryptor = TokenEncryptor()
    return Account(
        id=account_id,
        email=f"{account_id}@example.com",
        plan_type="plus",
        access_token_encrypted=encryptor.encrypt("access"),
        refresh_token_encrypted=encryptor.encrypt("refresh"),
        id_token_encrypted=encryptor.encrypt("id"),
        last_refresh=created_at,
        created_at=created_at,
        status=AccountStatus.ACTIVE,
        deactivation_reason=None,
        delete_requested_at=created_at if delete_requested else None,
    )


async def _seed() -> None:
    async with SessionLocal() as session:
        session.add(_account("acc_first", _CREATED))
        session.add(_account("acc_gone", _CREATED + timedelta(minutes=1), delete_requested=True))
        session.add(
            ModelSource(
                id="src_claude",
                name="Team Claude",
                kind="claude",
                base_url="https://claude.invalid",
                created_at=_CREATED + timedelta(minutes=2),
            )
        )
        session.add(_account("acc_third", _CREATED + timedelta(minutes=3)))
        await session.commit()


def _by_identity(payload: dict) -> dict[str, dict]:
    return {entry["accountId"] or entry["modelSourceId"]: entry for entry in payload["colors"]}


@pytest.mark.asyncio
async def test_colours_follow_creation_order_across_account_kinds(async_client, db_setup):
    await _seed()

    response = await async_client.get("/api/account-colors")

    assert response.status_code == 200
    colors = _by_identity(response.json())
    assert set(colors) == {"acc_first", "src_claude", "acc_third"}
    assert [colors[key]["color"] for key in ("acc_first", "src_claude", "acc_third")] == [0, 1, 2]


@pytest.mark.asyncio
async def test_picks_pin_colours_and_null_restores_automatic(async_client, db_setup):
    await _seed()

    picked = await async_client.put("/api/account-colors/model-sources/src_claude", json={"chartColor": 0})
    assert picked.status_code == 200
    colors = _by_identity(picked.json())
    assert colors["src_claude"] == {
        "accountId": None,
        "modelSourceId": "src_claude",
        "chartColor": 0,
        "color": 0,
        "automaticColor": 1,
    }
    assert colors["acc_first"]["color"] == 1
    assert colors["acc_third"]["color"] == 2

    pinned = await async_client.put("/api/account-colors/accounts/acc_third", json={"chartColor": 7})
    assert _by_identity(pinned.json())["acc_third"]["color"] == 7

    cleared = await async_client.put("/api/account-colors/model-sources/src_claude", json={"chartColor": None})
    colors = _by_identity(cleared.json())
    assert colors["src_claude"]["chartColor"] is None
    assert [colors[key]["color"] for key in ("acc_first", "src_claude", "acc_third")] == [0, 1, 7]


@pytest.mark.asyncio
async def test_rejects_unknown_targets_and_out_of_palette_picks(async_client, db_setup):
    await _seed()

    gone = await async_client.put("/api/account-colors/accounts/acc_gone", json={"chartColor": 3})
    assert gone.status_code == 404
    missing = await async_client.put("/api/account-colors/model-sources/missing", json={"chartColor": 3})
    assert missing.status_code == 404
    invalid = await async_client.put("/api/account-colors/accounts/acc_first", json={"chartColor": 12})
    assert invalid.status_code in {400, 422}
