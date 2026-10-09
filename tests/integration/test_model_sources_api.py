from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.db.models import ModelSource, RequestLog
from app.db.session import SessionLocal

pytestmark = pytest.mark.integration


async def _seed_claude_source() -> None:
    async with SessionLocal() as session:
        session.add(ModelSource(id="src_claude", name="Team Claude", kind="claude", base_url="https://claude.invalid"))
        await session.commit()


@pytest.mark.asyncio
async def test_provider_backed_sources_are_managed_only_through_their_account(async_client, db_setup):
    await _seed_claude_source()

    edited = await async_client.patch("/api/model-sources/src_claude", json={"name": "Renamed"})
    deleted = await async_client.delete("/api/model-sources/src_claude")

    for response in (edited, deleted):
        assert response.status_code == 400
        assert response.json()["error"]["message"] == "Manage Claude accounts through the Accounts dashboard"
    async with SessionLocal() as session:
        source = await session.get(ModelSource, "src_claude")
    assert source is not None
    assert source.name == "Team Claude"


@pytest.mark.asyncio
async def test_user_defined_source_trends_count_its_requests(async_client, db_setup):
    created = await async_client.post(
        "/api/model-sources/",
        json={"name": "LiteLLM", "baseUrl": "http://127.0.0.1:9/v1", "models": [{"model": "local-coder"}]},
    )
    source_id = created.json()["id"]
    async with SessionLocal() as session:
        session.add(
            RequestLog(
                request_id="req_source_trend",
                model_source_id=source_id,
                model="local-coder",
                status="success",
                requested_at=datetime.now(timezone.utc).replace(tzinfo=None),
            )
        )
        await session.commit()

    trends = await async_client.get(f"/api/model-sources/{source_id}/trends")
    missing = await async_client.get("/api/model-sources/src_missing/trends")

    assert trends.status_code == 200
    [series] = trends.json()["series"]
    assert series["key"] == "requests"
    assert sum(point["v"] or 0 for point in series["points"]) == 1
    assert missing.status_code == 404
