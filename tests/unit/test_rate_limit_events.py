from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock

import pytest

from app.core.types import JsonValue
from app.modules.proxy import api as proxy_api
from app.modules.proxy._service import rate_limit as rate_limit_module
from app.modules.proxy._service.rate_limit import _RateLimitMixin
from app.modules.proxy.rate_limit_events import (
    ClientUsageSnapshot,
    additional_rate_limit_events,
    project_rate_limit_event,
    rate_limit_event_from_headers,
)
from app.modules.proxy.types import AdditionalRateLimitData, RateLimitStatusDetailsData, RateLimitWindowSnapshotData

pytestmark = pytest.mark.unit

_POOL_HEADERS = {
    "x-codex-primary-used-percent": "7.0",
    "x-codex-primary-window-minutes": "300",
    "x-codex-primary-reset-at": "1000",
    "x-codex-secondary-used-percent": "30.5",
    "x-codex-secondary-window-minutes": "10080",
    "x-codex-credits-has-credits": "true",
    "x-codex-credits-unlimited": "false",
    "x-codex-credits-balance": "8.75",
}

_ACCOUNT_EVENT: dict[str, JsonValue] = {
    "type": "codex.rate_limits",
    "plan_type": "plus",
    "rate_limits": {
        "primary": {"used_percent": 100.0, "window_minutes": 300, "reset_at": 900},
        "secondary": {"used_percent": 56.0, "window_minutes": 10080, "reset_at": 7000},
    },
    "credits": {"has_credits": False, "unlimited": False, "balance": "0"},
}


def test_codex_event_is_replaced_with_the_pool_snapshot() -> None:
    projected = project_rate_limit_event(_ACCOUNT_EVENT, ClientUsageSnapshot(headers=_POOL_HEADERS))

    assert projected == {
        "type": "codex.rate_limits",
        "rate_limits": {
            "primary": {"used_percent": 7.0, "window_minutes": 300, "reset_at": 1000},
            "secondary": {"used_percent": 30.5, "window_minutes": 10080, "reset_at": None},
        },
        "credits": {"has_credits": True, "unlimited": False, "balance": "8.75"},
    }


def test_event_is_withheld_without_a_pool_snapshot() -> None:
    assert project_rate_limit_event(_ACCOUNT_EVENT, None) is None
    assert project_rate_limit_event(_ACCOUNT_EVENT, ClientUsageSnapshot(headers={})) is None


def test_additional_family_gets_its_pool_aggregate() -> None:
    spark = AdditionalRateLimitData(
        quota_key="codex_spark",
        limit_name="GPT-5.3-Codex-Spark",
        metered_feature="codex_bengalfox",
        rate_limit=RateLimitStatusDetailsData(
            allowed=True,
            limit_reached=False,
            primary_window=RateLimitWindowSnapshotData(used_percent=12, limit_window_seconds=18_000, reset_at=500),
        ),
    )
    snapshot = ClientUsageSnapshot(headers=_POOL_HEADERS, additional=additional_rate_limit_events([spark]))
    event: dict[str, JsonValue] = {**_ACCOUNT_EVENT, "metered_limit_name": "codex_bengalfox"}

    assert project_rate_limit_event(event, snapshot) == {
        "type": "codex.rate_limits",
        "metered_limit_name": "codex_bengalfox",
        "rate_limits": {
            "primary": {"used_percent": 12.0, "window_minutes": 300, "reset_at": 500},
            "secondary": None,
        },
    }


def test_unknown_additional_family_is_withheld() -> None:
    event: dict[str, JsonValue] = {**_ACCOUNT_EVENT, "limit_name": "codex_unknown"}

    assert project_rate_limit_event(event, ClientUsageSnapshot(headers=_POOL_HEADERS)) is None


def test_event_from_headers_omits_unknown_credits() -> None:
    event = rate_limit_event_from_headers({"x-codex-primary-used-percent": "40.0"})

    assert event == {
        "type": "codex.rate_limits",
        "rate_limits": {
            "primary": {"used_percent": 40.0, "window_minutes": None, "reset_at": None},
            "secondary": None,
        },
    }


@pytest.mark.parametrize("hidden", [False, True])
async def test_openai_event_is_the_pool_snapshot_unless_quota_is_hidden(monkeypatch, hidden: bool) -> None:
    service = SimpleNamespace(openai_client_usage=AsyncMock(return_value=ClientUsageSnapshot(headers=_POOL_HEADERS)))
    monkeypatch.setattr(rate_limit_module, "hide_upstream_quota_for_api_key_clients", AsyncMock(return_value=hidden))

    event = await _RateLimitMixin.openai_rate_limit_event(cast(Any, service), _ACCOUNT_EVENT, cast(Any, object()))

    if hidden:
        assert event is None
    else:
        assert event is not None
        assert event["rate_limits"] == {
            "primary": {"used_percent": 7.0, "window_minutes": 300, "reset_at": 1000},
            "secondary": {"used_percent": 30.5, "window_minutes": 10080, "reset_at": None},
        }


@pytest.mark.parametrize(
    ("kind", "hidden", "expected"),
    [
        ("claude", False, {"x-codex-primary-used-percent": "12.0"}),
        ("claude", True, {}),
        ("openrouter", False, {}),
        ("openai_compatible", False, {}),
    ],
)
async def test_source_turns_report_only_the_claude_pool(monkeypatch, kind, hidden, expected) -> None:
    claude_headers = AsyncMock(return_value={"x-codex-primary-used-percent": "12.0"})
    context = SimpleNamespace(service=SimpleNamespace(claude_rate_limit_headers=claude_headers))
    monkeypatch.setattr(proxy_api, "_hide_upstream_quota_for_api_key_clients", AsyncMock(return_value=hidden))

    headers = await proxy_api._rate_limit_headers_for_source(
        cast(Any, context), None, cast(Any, SimpleNamespace(kind=kind)), "claude-opus-5-5"
    )

    assert headers == expected
    if expected:
        claude_headers.assert_awaited_once_with("claude-opus-5-5")
