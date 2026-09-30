from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import func, select

from app.db.models import ClaudeQuotaHistory, RequestLog
from app.db.session import SessionLocal
from app.modules.claude.client import ClaudeClient
from app.modules.claude.credentials import ClaudeError
from app.modules.claude.repository import ClaudeRepository
from app.modules.claude.schemas import QuotaWindow, UsageSnapshot
from tests.integration.test_claude_accounts import import_body, install_profile_stub
from tests.integration.test_openrouter_accounts import provider  # noqa: F401

pytestmark = pytest.mark.integration


@pytest.mark.usefixtures("provider")
async def test_openrouter_activity_is_account_scoped_and_hourly(async_client):
    ids = []
    for name in ("A", "B"):
        response = await async_client.post("/api/openrouter-accounts", json={"name": name, "apiKey": "test-key"})
        assert response.status_code == 200, response.text
        ids.append(response.json()["id"])
    at = datetime.now(UTC).replace(tzinfo=None, minute=45, second=0, microsecond=0) - timedelta(hours=1)
    async with SessionLocal() as session:
        for index, (source, deleted, days) in enumerate(
            [
                (ids[0], False, 0),
                (ids[0], False, 0),
                (ids[1], False, 0),
                (ids[0], True, 0),
                (ids[0], False, 9),
            ]
        ):
            session.add(
                RequestLog(
                    model_source_id=source,
                    requested_at=at - timedelta(days=days),
                    deleted_at=at if deleted else None,
                    request_id=f"trend-{index}",
                    model="test",
                    status="success",
                )
            )
        await session.commit()
    result = (await async_client.get(f"/api/openrouter-accounts/{ids[0]}/trends")).json()
    series = result["series"]
    assert [s["key"] for s in series] == ["requests"]
    assert len(series[0]["points"]) == 168
    assert sum(p["v"] for p in series[0]["points"]) == 2
    observed = next(p for p in series[0]["points"] if p["v"])
    assert datetime.fromisoformat(observed["t"].replace("Z", "+00:00")).hour == at.hour
    assert (await async_client.get("/api/openrouter-accounts/missing/trends")).status_code == 404
    assert (await async_client.get(f"/api/claude-accounts/{ids[0]}/trends")).status_code == 404


async def test_claude_refresh_records_history_and_failure_does_not(async_client, monkeypatch):
    install_profile_stub(monkeypatch)
    source = (await async_client.post("/api/claude-accounts/import", json=import_body())).json()["id"]
    assert (await async_client.get(f"/api/claude-accounts/{source}/trends")).json() == {"series": []}
    monkeypatch.setattr(ClaudeClient, "catalog", AsyncMock(return_value=[]))
    monkeypatch.setattr(
        ClaudeClient,
        "usage",
        AsyncMock(
            return_value=UsageSnapshot(five_hour=QuotaWindow(utilization=30), seven_day=QuotaWindow(utilization=80))
        ),
    )
    response = await async_client.post(f"/api/claude-accounts/{source}/refresh")
    assert response.status_code == 200, response.text
    assert [window["name"] for window in response.json()["quota"]["windows"]] == ["five_hour", "seven_day"]
    result = (await async_client.get(f"/api/claude-accounts/{source}/trends")).json()
    assert [s["key"] for s in result["series"]] == ["five_hour", "seven_day"]
    assert [p["v"] for p in result["series"][0]["points"] if p["v"] is not None] == [70]
    assert sum(p["v"] is None for p in result["series"][0]["points"]) == 167
    monkeypatch.setattr(ClaudeClient, "usage", AsyncMock(side_effect=ClaudeError("unavailable")))
    await async_client.post(f"/api/claude-accounts/{source}/refresh")
    async with SessionLocal() as session:
        assert await session.scalar(select(func.count()).select_from(ClaudeQuotaHistory)) == 2
    await async_client.delete(f"/api/claude-accounts/{source}")
    async with SessionLocal() as session:
        assert await session.scalar(select(func.count()).select_from(ClaudeQuotaHistory)) == 0


async def test_claude_history_is_transactional_and_pruned_on_refresh(async_client, monkeypatch):
    install_profile_stub(monkeypatch)
    source = (await async_client.post("/api/claude-accounts/import", json=import_body())).json()["id"]
    usage = UsageSnapshot(five_hour=QuotaWindow(utilization=60))
    async with SessionLocal() as session:
        repository = ClaudeRepository(session)
        await repository.record_quota(source, usage, datetime.now(UTC) - timedelta(days=31))
        await session.commit()
        await repository.record_quota(source, usage, datetime.now(UTC))
        await session.rollback()
        assert await session.scalar(select(func.count()).select_from(ClaudeQuotaHistory)) == 1
        await repository.record_quota(source, usage, datetime.now(UTC))
        await session.commit()
        rows = list(await session.scalars(select(ClaudeQuotaHistory)))
        assert len(rows) == 1 and rows[0].observed_at > datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=1)


def test_quota_history_migration_roundtrip(tmp_path):
    from alembic import command
    from sqlalchemy import create_engine, inspect

    from app.db.migrate import _build_alembic_config, check_schema_drift, run_upgrade

    url = f"sqlite:///{tmp_path / 'trends.db'}"
    config = _build_alembic_config(url)
    run_upgrade(url, bootstrap_legacy=False)
    assert check_schema_drift(url) == ()
    engine = create_engine(url)
    try:
        assert "claude_quota_history" in inspect(engine).get_table_names()
        command.downgrade(config, "20260926_000000_quota_reset_webhook")
        assert "claude_quota_history" not in inspect(engine).get_table_names()
        run_upgrade(url, bootstrap_legacy=False)
        assert check_schema_drift(url) == ()
    finally:
        engine.dispose()


async def test_claude_reset_deadline_persists_with_weekly_plan_api(async_client, monkeypatch):
    install_profile_stub(monkeypatch)
    source = (await async_client.post("/api/claude-accounts/import", json=import_body())).json()["id"]
    reset = datetime.now(UTC) + timedelta(days=3)
    monkeypatch.setattr(ClaudeClient, "catalog", AsyncMock(return_value=[]))
    monkeypatch.setattr(
        ClaudeClient,
        "usage",
        AsyncMock(
            return_value=UsageSnapshot(
                seven_day=QuotaWindow(utilization=20, resets_at=reset),
            )
        ),
    )
    response = await async_client.post(f"/api/claude-accounts/{source}/refresh")
    assert response.status_code == 200, response.text
    async with SessionLocal() as session:
        row = await session.scalar(select(ClaudeQuotaHistory).where(ClaudeQuotaHistory.source_id == source))
        assert row.resets_at == reset.replace(tzinfo=None)
    series = (await async_client.get(f"/api/claude-accounts/{source}/trends")).json()["series"]
    assert [s["key"] for s in series] == ["seven_day", "weekly_plan"]
    measured, guideline = series
    assert measured["colorIndex"] == guideline["colorIndex"] == 1
    assert guideline["dashed"] and not measured["dashed"]
    assert all(42 < p["v"] < 43 for p in guideline["points"] if p["v"] is not None)


async def test_sampling_preserves_reset_changes_within_interval(async_client, monkeypatch):
    install_profile_stub(monkeypatch)
    source = (await async_client.post("/api/claude-accounts/import", json=import_body())).json()["id"]
    at = datetime(2026, 9, 30, 12, tzinfo=UTC)
    reset = at + timedelta(days=3)
    async with SessionLocal() as session:
        repository = ClaudeRepository(session)
        for seconds, deadline in [(0, reset), (10, reset), (20, reset + timedelta(days=7)), (30, None)]:
            await repository.record_quota(
                source,
                UsageSnapshot(seven_day=QuotaWindow(utilization=20, resets_at=deadline)),
                at + timedelta(seconds=seconds),
                sample_seconds=60,
            )
            await session.flush()
        await session.commit()
        rows = list(
            await session.scalars(
                select(ClaudeQuotaHistory)
                .where(ClaudeQuotaHistory.source_id == source)
                .order_by(ClaudeQuotaHistory.observed_at)
            )
        )
        assert [row.observed_at.second for row in rows] == [0, 20, 30]
        assert [row.resets_at for row in rows] == [
            reset.replace(tzinfo=None),
            (reset + timedelta(days=7)).replace(tzinfo=None),
            None,
        ]


def test_deadline_migration_preserves_legacy_rows(tmp_path):
    from alembic import command
    from sqlalchemy import create_engine, inspect, text

    from app.db.migrate import _build_alembic_config, check_schema_drift, run_upgrade

    url = f"sqlite:///{tmp_path / 'deadlines.db'}"
    config = _build_alembic_config(url)
    run_upgrade(url, revision="20260929_040000_claude_usage_detail", bootstrap_legacy=False)
    engine = create_engine(url)
    try:
        with engine.begin() as conn:
            # SQLite fixture connection does not enable FK checks; only the legacy sample matters here.
            conn.execute(
                text(
                    "INSERT INTO claude_quota_history (source_id, observed_at, window, used_percent) "
                    "VALUES ('legacy', '2026-09-29 12:00:00', 'seven_day', 20)"
                )
            )
        run_upgrade(url, bootstrap_legacy=False)
        assert check_schema_drift(url) == ()
        with engine.connect() as conn:
            assert conn.execute(text("SELECT used_percent, resets_at FROM claude_quota_history")).one() == (20, None)
        command.downgrade(config, "20260929_040000_claude_usage_detail")
        assert "resets_at" not in {column["name"] for column in inspect(engine).get_columns("claude_quota_history")}
        run_upgrade(url, bootstrap_legacy=False)
        assert check_schema_drift(url) == ()
    finally:
        engine.dispose()
