from __future__ import annotations

import time
from collections.abc import Awaitable, Callable, Hashable

import anyio

from app.core.usage.refresh_policy import USAGE_REFRESH_INTERVAL_SECONDS
from app.modules.proxy.rate_limit_events import ClientUsageSnapshot


class ClientUsageCache:
    """Pool usage snapshots per provider pool, refreshed once per usage interval."""

    def __init__(self) -> None:
        self._entries: dict[Hashable, tuple[float, ClientUsageSnapshot]] = {}
        self._lock = anyio.Lock()

    async def get(
        self,
        key: Hashable,
        compute: Callable[[], Awaitable[ClientUsageSnapshot]],
    ) -> ClientUsageSnapshot:
        cached = self._fresh(key)
        if cached is not None:
            return cached
        async with self._lock:
            cached = self._fresh(key)
            if cached is not None:
                return cached
            snapshot = await compute()
            self._entries[key] = (time.monotonic(), snapshot)
            return snapshot

    async def invalidate(self) -> None:
        async with self._lock:
            self._entries.clear()

    def _fresh(self, key: Hashable) -> ClientUsageSnapshot | None:
        entry = self._entries.get(key)
        if entry is None or time.monotonic() - entry[0] >= USAGE_REFRESH_INTERVAL_SECONDS:
            return None
        return entry[1]


_client_usage_cache = ClientUsageCache()


def get_client_usage_cache() -> ClientUsageCache:
    return _client_usage_cache
