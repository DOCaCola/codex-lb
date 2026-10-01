from dataclasses import replace
from datetime import timedelta
from unittest.mock import AsyncMock

import pytest

import app.core.auth.dependencies as auth_dependencies
from app.core.auth.dashboard_access import guest_principal
from app.core.utils.time import utcnow
from app.db.models import RequestLog
from app.db.session import SessionLocal
from tests.integration.test_conversations_api import _account

pytestmark = pytest.mark.integration


async def seed(*rows):
    async with SessionLocal() as session:
        session.add_all(rows)
        await session.commit()


def log(identifier, now, **overrides):
    return RequestLog(
        **{
            "request_id": identifier,
            "model": "anthropic/claude-opus-5-5",
            "status": "success",
            "requested_at": now,
            "request_kind": "normal",
            "request_operation": "messages",
            "model_source_id": "source-a",
            "model_source_kind": "claude",
            "conversation_id": "observed-conversation",
            "input_tokens": 1000,
            "cached_input_tokens": 800,
            "cache_creation_tokens": 100,
            "output_tokens": 100,
            "reasoning_tokens": 20,
            "latency_first_token_ms": 1000,
            "latency_ms": 3000,
            **overrides,
        }
    )


async def test_cache_activity_uses_complete_normal_measurements_without_double_counting(async_client, monkeypatch):
    now = utcnow().replace(microsecond=0)
    monkeypatch.setattr("app.modules.request_logs.api.utcnow", lambda: now)
    await seed(
        log("previous", now - timedelta(minutes=90), cached_input_tokens=500),
        log("current", now - timedelta(minutes=30)),
        log("zero", now - timedelta(minutes=10), cached_input_tokens=0, cache_creation_tokens=0),
        log("unknown", now - timedelta(minutes=20), cache_creation_tokens=None),
        log("invalid-cache", now - timedelta(minutes=20), cached_input_tokens=2000),
        log("failed", now - timedelta(minutes=5), status="error"),
        log("warmup", now - timedelta(minutes=5), request_kind="warmup"),
        log("deleted", now - timedelta(minutes=5), deleted_at=now),
        log("compact", now - timedelta(minutes=5), request_operation="compaction"),
        log("too-old", now - timedelta(hours=3)),
        log("boundary-end", now),
        log("other-source", now - timedelta(minutes=5), model_source_id="source-b", input_tokens=None),
    )
    response = await async_client.get("/api/request-logs/claude-cache-activity")
    assert response.status_code == 200, response.text
    body = response.json()
    groups = {group["sourceId"]: group for group in body["groups"]}
    group = groups["source-a"]
    assert group["current"] == {
        "requests": 4,
        "measuredRequests": 2,
        "inputTokens": 2000,
        "cacheReadTokens": 800,
        "cacheWriteTokens": 100,
        "cacheReadRatio": 0.4,
    }
    assert group["previous"]["cacheReadRatio"] == 0.5
    assert group["readRatioChange"] == pytest.approx(-0.1)
    assert groups["source-b"]["current"]["cacheReadRatio"] is None
    assert groups["source-b"]["previous"]["requests"] == 0


async def test_conversation_analytics_measurement_scope_accounts_and_unknowns(async_client):
    now = utcnow().replace(microsecond=0)
    async with SessionLocal() as session:
        session.add(_account("source-a"))  # Same text ID, distinct native/source namespaces.
        await session.commit()
    await seed(
        log("claude", now - timedelta(minutes=10)),
        log(
            "router",
            now - timedelta(minutes=5),
            model="openrouter/test",
            model_source_kind="openrouter",
            model_source_id="router",
        ),
        log("native", now, model="gpt-test", model_source_id=None, model_source_kind=None, account_id="source-a"),
        log(
            "missing",
            now - timedelta(minutes=9),
            model="unknown",
            latency_first_token_ms=None,
            cache_creation_tokens=None,
        ),
        log("error", now - timedelta(minutes=8), status="error"),
        log("cancel", now - timedelta(minutes=7), status="cancelled"),
        log("compact", now - timedelta(minutes=6), request_operation="compaction", latency_ms=100000),
        log("historical", now - timedelta(days=8), model="old-only"),
        log("deleted", now - timedelta(minutes=5), deleted_at=now, model_source_id="deleted-source"),
    )
    response = await async_client.get("/api/conversations/observed-conversation")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["accountCount"] == 3
    assert "old-only" in {row["modelEffort"]["model"] for row in body["modelStats"]}
    analytics = body["analytics"]
    models = {row["model"]: row for row in analytics["models"]}
    assert "old-only" not in models
    claude = models["anthropic/claude-opus-5-5"]
    assert (claude["errors"], claude["cancelled"]) == (1, 1)
    assert (claude["ttftSamples"], claude["tpsSamples"]) == (1, 1)
    assert claude["meanTtftMs"] == 1000
    assert claude["meanTps"] == 40
    assert models["openrouter/test"]["meanTps"] == 50
    assert models["unknown"]["meanTtftMs"] is None
    assert models["unknown"]["meanTps"] is None
    assert models["unknown"]["cacheWriteSamples"] == 0
    assert sum(row["requests"] for row in analytics["activity"]) == 7
    assert sum(row["errors"] for row in analytics["activity"]) == 1
    assert sum(row["cancelled"] for row in analytics["activity"]) == 1


async def test_empty_cache_activity_is_an_observation_not_health_failure(async_client):
    response = await async_client.get("/api/request-logs/claude-cache-activity")
    assert response.status_code == 200
    assert response.json()["groups"] == []


async def test_cache_activity_requires_account_read_permission(async_client, monkeypatch):
    principal = replace(guest_principal(), grants={}, permissions=frozenset())
    dependency = auth_dependencies.validate_dashboard_session
    monkeypatch.setattr(auth_dependencies, "validate_dashboard_session", AsyncMock(return_value=principal))
    monkeypatch.setitem(async_client._transport.app.dependency_overrides, dependency, lambda: principal)
    response = await async_client.get("/api/request-logs/claude-cache-activity")
    assert response.status_code == 403, response.text
