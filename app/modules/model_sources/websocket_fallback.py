from __future__ import annotations

import time
from collections.abc import Mapping

SOURCE_WEBSOCKET_FALLBACK_TTL_SECONDS = 60.0
SOURCE_WEBSOCKET_FALLBACK_CAPACITY = 4096
_SOURCE_WEBSOCKET_FALLBACK_IDENTITY_HEADERS = ("x-codex-turn-state", "thread-id")


def source_websocket_fallback_identities(headers: Mapping[str, str]) -> tuple[str, ...]:
    normalized_headers = {name.lower(): value for name, value in headers.items()}
    identities = (normalized_headers.get(name, "").strip() for name in _SOURCE_WEBSOCKET_FALLBACK_IDENTITY_HEADERS)
    return tuple(dict.fromkeys(identity for identity in identities if identity))


class SourceWebSocketFallbackRegistry:
    """Coordinate source-model retries between WebSocket and HTTP transports."""

    def __init__(
        self,
        *,
        ttl_seconds: float = SOURCE_WEBSOCKET_FALLBACK_TTL_SECONDS,
        capacity: int = SOURCE_WEBSOCKET_FALLBACK_CAPACITY,
    ) -> None:
        self._ttl_seconds = ttl_seconds
        self._capacity = capacity
        self._entries: dict[tuple[str, str | None], float] = {}

    def mark(self, identity: str | None, api_key_id: str | None) -> None:
        normalized_identity = self._normalize_identity(identity)
        if normalized_identity is None:
            return

        now = time.monotonic()
        self._prune(now)
        key = (normalized_identity, api_key_id)
        self._entries.pop(key, None)
        self._entries[key] = now + self._ttl_seconds
        while len(self._entries) > self._capacity:
            self._entries.pop(next(iter(self._entries)))

    def matches(self, identity: str | None, api_key_id: str | None) -> bool:
        normalized_identity = self._normalize_identity(identity)
        if normalized_identity is None:
            return False

        now = time.monotonic()
        self._prune(now)
        return (normalized_identity, api_key_id) in self._entries

    def _prune(self, now: float) -> None:
        expired = [key for key, expires_at in self._entries.items() if expires_at <= now]
        for key in expired:
            self._entries.pop(key)

    @staticmethod
    def _normalize_identity(identity: str | None) -> str | None:
        if identity is None:
            return None
        normalized = identity.strip()
        return normalized or None
