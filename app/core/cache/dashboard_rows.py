"""Process-wide snapshot of a dashboard-managed table, shared by its readers.

Mirrors ``SettingsCache``: a short TTL bounds staleness for out-of-band database
edits, and the settings API invalidates durably through the ``settings``
namespace so every replica drops its snapshot at once.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod

import anyio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache.invalidation import NAMESPACE_SETTINGS, get_cache_invalidation_poller


class DashboardRowsCache[T](ABC):
    # An expired snapshot is never fresh, whatever ``time.monotonic()`` returns
    # this early after boot; 0.0 would read as fresh for the first TTL seconds
    # of process uptime.
    _EXPIRED = float("-inf")

    def __init__(self, *, ttl_seconds: float = 5.0) -> None:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        self._ttl_seconds = ttl_seconds
        self._cached: T | None = None
        self._cached_at = self._EXPIRED
        self._lock = anyio.Lock()

    @abstractmethod
    async def _load(self, session: AsyncSession) -> T:
        """Read the current rows."""

    async def get(self) -> T:
        now = time.monotonic()
        if self._cached is not None and now - self._cached_at < self._ttl_seconds:
            return self._cached

        async with self._lock:
            now = time.monotonic()
            if self._cached is not None and now - self._cached_at < self._ttl_seconds:
                return self._cached
            # Imported lazily: ``app.db.session`` builds the engine from the
            # process settings on import, which unit tests must not trigger.
            from app.db.session import SessionLocal

            try:
                async with SessionLocal() as session:
                    rows = await self._load(session)
            except Exception:
                # Readers must not fail because the database is briefly
                # unreachable: keep serving the last known rows (like
                # ``SettingsCache.cached_row``) and retry on the next call. The
                # timestamp is deliberately not refreshed.
                if self._cached is None:
                    raise
                return self._cached
            self._cached = rows
            self._cached_at = now
            return rows

    def clear(self) -> None:
        """Forget the snapshot entirely, without taking the lock.

        Only for process-local resets with no concurrent load (test teardown);
        every runtime path goes through ``invalidate``, which keeps the last
        known rows as a fallback.
        """
        self._cached = None
        self._cached_at = self._EXPIRED

    async def invalidate(self, *, propagate: bool = True) -> None:
        """Drop the snapshot and, unless ``propagate`` is False, durably bump the
        cross-replica ``settings`` namespace before returning.

        Only the snapshot's *freshness* is dropped, not the rows: the next
        ``get`` always reloads, but a load that fails while the database is
        briefly unreachable can still fall back to the last known rows.
        Settings-namespace bumps are frequent and mostly unrelated to a given
        table, so forgetting the rows on every one of them would make the
        fallback almost never available.

        The expiry happens under the lock, like ``SettingsCache``: a load
        already inside ``get`` and awaiting the database must finish before
        the snapshot is expired, otherwise it would install its pre-write rows
        afterwards and keep serving them until the TTL expires. The poller
        callback registered for the namespace passes ``propagate=False`` so a
        remote bump never re-bumps (feedback-loop prevention).
        """
        async with self._lock:
            self._cached_at = self._EXPIRED
        if propagate:
            poller = get_cache_invalidation_poller()
            if poller is not None:
                await poller.bump(NAMESPACE_SETTINGS)
