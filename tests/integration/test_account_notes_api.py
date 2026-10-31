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


async def _seed() -> None:
    async with SessionLocal() as session:
        session.add(_account("acc_live"))
        session.add(_account("acc_gone", delete_requested=True))
        session.add(
            ModelSource(
                id="src_claude",
                name="Team Claude",
                kind="claude",
                base_url="https://claude.invalid",
                created_at=_CREATED,
            )
        )
        await session.commit()


def _by_identity(payload: dict) -> dict[str, str]:
    return {entry["accountId"] or entry["modelSourceId"]: entry["note"] for entry in payload["notes"]}


@pytest.mark.asyncio
async def test_notes_are_saved_trimmed_and_cleared(async_client, db_setup):
    await _seed()

    assert (await async_client.get("/api/account-notes")).json() == {"notes": []}

    saved = await async_client.put(
        "/api/account-notes/accounts/acc_live", json={"note": "  Shared with ops.\nRenew in May.  "}
    )
    assert saved.status_code == 200
    assert _by_identity(saved.json()) == {"acc_live": "Shared with ops.\nRenew in May."}

    source = await async_client.put("/api/account-notes/model-sources/src_claude", json={"note": "Pro plan"})
    assert _by_identity(source.json()) == {"acc_live": "Shared with ops.\nRenew in May.", "src_claude": "Pro plan"}

    blank = await async_client.put("/api/account-notes/accounts/acc_live", json={"note": "   "})
    assert _by_identity(blank.json()) == {"src_claude": "Pro plan"}

    cleared = await async_client.put("/api/account-notes/model-sources/src_claude", json={"note": None})
    assert cleared.json() == {"notes": []}


@pytest.mark.asyncio
async def test_rejects_unknown_targets_and_overlong_notes(async_client, db_setup):
    await _seed()

    gone = await async_client.put("/api/account-notes/accounts/acc_gone", json={"note": "x"})
    assert gone.status_code == 404
    assert gone.json()["error"]["code"] == "account_not_found"
    missing = await async_client.put("/api/account-notes/model-sources/missing", json={"note": "x"})
    assert missing.status_code == 404
    overlong = await async_client.put("/api/account-notes/accounts/acc_live", json={"note": "x" * 2001})
    assert overlong.status_code in {400, 422}
