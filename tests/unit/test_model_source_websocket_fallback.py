from __future__ import annotations

import pytest

import app.modules.model_sources.websocket_fallback as fallback_module
from app.modules.model_sources.websocket_fallback import (
    SourceWebSocketFallbackRegistry,
    source_websocket_fallback_identities,
)


def test_fallback_identities_are_conversation_scoped() -> None:
    assert source_websocket_fallback_identities(
        {
            "X-Codex-Turn-State": " turn-state ",
            "Thread-Id": "thread-id",
            "Session-Id": "process-wide-session",
        }
    ) == ("turn-state", "thread-id")


def test_fallback_registry_is_scoped_by_identity_and_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    now = 100.0
    monkeypatch.setattr(fallback_module.time, "monotonic", lambda: now)
    registry = SourceWebSocketFallbackRegistry(ttl_seconds=10)

    registry.mark("conversation-a", "key-a")

    assert registry.matches("conversation-a", "key-a") is True
    assert registry.matches("conversation-b", "key-a") is False
    assert registry.matches("conversation-a", "key-b") is False

    now = 111.0
    assert registry.matches("conversation-a", "key-a") is False


def test_fallback_registry_bounds_capacity(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(fallback_module.time, "monotonic", lambda: 100.0)
    registry = SourceWebSocketFallbackRegistry(capacity=2)

    registry.mark("oldest", None)
    registry.mark("middle", None)
    registry.mark("newest", None)

    assert registry.matches("oldest", None) is False
    assert registry.matches("middle", None) is True
    assert registry.matches("newest", None) is True
