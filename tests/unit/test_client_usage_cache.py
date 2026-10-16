from __future__ import annotations

import pytest

import app.modules.proxy.client_usage_cache as client_usage_cache_module
from app.modules.proxy.client_usage_cache import ClientUsageCache
from app.modules.proxy.rate_limit_events import ClientUsageSnapshot

pytestmark = pytest.mark.unit


def _counting_compute(state: dict[str, float]):
    async def compute() -> ClientUsageSnapshot:
        state["calls"] += 1
        return ClientUsageSnapshot(headers={"x-header": f"v{int(state['calls'])}"})

    return compute


@pytest.mark.asyncio
async def test_cache_hit_within_ttl(monkeypatch: pytest.MonkeyPatch) -> None:
    state = {"now": 100.0, "calls": 0}
    monkeypatch.setattr(client_usage_cache_module.time, "monotonic", lambda: state["now"])
    cache = ClientUsageCache()
    compute = _counting_compute(state)

    first = await cache.get("openai", compute)
    second = await cache.get("openai", compute)

    assert first is second
    assert state["calls"] == 1
    assert first.headers == {"x-header": "v1"}


@pytest.mark.asyncio
async def test_cache_keeps_pools_apart(monkeypatch: pytest.MonkeyPatch) -> None:
    state = {"now": 100.0, "calls": 0}
    monkeypatch.setattr(client_usage_cache_module.time, "monotonic", lambda: state["now"])
    cache = ClientUsageCache()
    compute = _counting_compute(state)

    openai = await cache.get("openai", compute)
    claude = await cache.get(("claude", ("five_hour", "seven_day")), compute)

    assert openai is not claude
    assert await cache.get("openai", compute) is openai
    assert state["calls"] == 2


@pytest.mark.asyncio
async def test_cache_recompute_after_ttl_expiry(monkeypatch: pytest.MonkeyPatch) -> None:
    state = {"now": 100.0, "calls": 0}
    monkeypatch.setattr(client_usage_cache_module.time, "monotonic", lambda: state["now"])
    cache = ClientUsageCache()
    compute = _counting_compute(state)

    first = await cache.get("openai", compute)
    state["now"] = 161.0  # past 60s TTL
    second = await cache.get("openai", compute)

    assert second is not first
    assert second.headers == {"x-header": "v2"}


@pytest.mark.asyncio
async def test_cache_recompute_after_invalidate(monkeypatch: pytest.MonkeyPatch) -> None:
    state = {"now": 100.0, "calls": 0}
    monkeypatch.setattr(client_usage_cache_module.time, "monotonic", lambda: state["now"])
    cache = ClientUsageCache()
    compute = _counting_compute(state)

    first = await cache.get("openai", compute)
    await cache.invalidate()
    second = await cache.get("openai", compute)

    assert second is not first
    assert state["calls"] == 2
