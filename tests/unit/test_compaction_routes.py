from __future__ import annotations

from types import SimpleNamespace
from typing import cast

import pytest

from app.core.openai import compaction_routes as compaction_routes_module
from app.core.openai.compaction_routes import (
    CompactionRoute,
    CompactionRouteIncompatibility,
    compaction_route_incompatibility,
    compaction_routes_for,
    is_native_compaction_request,
)
from app.core.openai.model_registry import ModelRegistry
from app.core.openai.requests import ResponsesCompactRequest, ResponsesRequest
from app.modules.api_keys.service import ApiKeyData
from app.modules.proxy.request_policy import apply_api_key_enforcement

_LUNA = CompactionRoute("gpt-6-astra", "gpt-5.6-luna", "low")
_TRIGGER_INPUT = [
    {"role": "user", "content": [{"type": "input_text", "text": "work"}]},
    {"type": "compaction_trigger"},
]


def _incompatibility(
    route: CompactionRoute,
    *,
    routes: dict[str, CompactionRoute] | None = None,
    client_windows: dict[str, int] | None = None,
) -> CompactionRouteIncompatibility | None:
    return compaction_route_incompatibility(
        route,
        routes=routes if routes is not None else {route.slug: route},
        registry=ModelRegistry(ttl_seconds=60.0),
        client_windows=client_windows or {},
    )


def _api_key(**fields: object) -> ApiKeyData:
    defaults: dict[str, object] = {
        "id": "key-compaction",
        "allowed_models": None,
        "enforced_model": None,
        "enforced_reasoning_effort": None,
        "enforced_service_tier": None,
        "allowed_reasoning_efforts": None,
    }
    return cast(ApiKeyData, SimpleNamespace(**(defaults | fields)))


def _trigger_request(model: str = "gpt-6-astra", effort: str = "high") -> ResponsesRequest:
    return ResponsesRequest.model_validate(
        {"model": model, "instructions": "", "input": _TRIGGER_INPUT, "reasoning": {"effort": effort}}
    )


def test_route_between_models_sharing_the_checkpoint_format_is_compatible() -> None:
    assert _incompatibility(_LUNA) is None
    assert _incompatibility(CompactionRoute("gpt-6-astra", "gpt-5.6-luna", "max")) is None
    assert _incompatibility(CompactionRoute("gpt-6-astra", "gpt-5.6-sol", None)) is None
    # Only another effort on the same model is a route too.
    assert _incompatibility(CompactionRoute("gpt-6-astra", "gpt-6-astra", "low")) is None


@pytest.mark.parametrize(
    ("route", "reason"),
    [
        (CompactionRoute("gpt-unknown", "gpt-5.6-luna", None), CompactionRouteIncompatibility.CODING_MODEL_UNAVAILABLE),
        (
            CompactionRoute("gpt-6-astra", "gpt-unknown", None),
            CompactionRouteIncompatibility.COMPACTION_MODEL_UNAVAILABLE,
        ),
        (CompactionRoute("gpt-6-astra", "gpt-6-astra", None), CompactionRouteIncompatibility.NOTHING_CHANGES),
        (CompactionRoute("gpt-6-astra", "gpt-5.5", None), CompactionRouteIncompatibility.CHECKPOINT_FORMAT_MISMATCH),
        (CompactionRoute("gpt-6-astra", "gpt-5.6-luna", "ultra"), CompactionRouteIncompatibility.EFFORT_UNSUPPORTED),
    ],
)
def test_incompatible_routes_report_their_reason(
    route: CompactionRoute, reason: CompactionRouteIncompatibility
) -> None:
    assert _incompatibility(route) == reason


def test_compaction_model_must_accept_the_coding_models_client_window() -> None:
    # Luna's ceiling is its 872k max_context_window, not its 272k default window.
    assert _incompatibility(_LUNA, client_windows={"gpt-6-astra": 800_000}) is None
    assert (
        _incompatibility(_LUNA, client_windows={"gpt-6-astra": 900_000})
        == CompactionRouteIncompatibility.CONTEXT_WINDOW_TOO_SMALL
    )


def test_compaction_model_with_a_route_of_its_own_is_rejected() -> None:
    routes = {_LUNA.slug: _LUNA, "gpt-5.6-luna": CompactionRoute("gpt-5.6-luna", "gpt-5.6-terra", None)}
    assert _incompatibility(_LUNA, routes=routes) == CompactionRouteIncompatibility.COMPACTION_MODEL_ROUTED


def test_native_compaction_requests_are_the_compact_endpoint_and_trigger_input() -> None:
    assert is_native_compaction_request(ResponsesCompactRequest(model="gpt-6-astra", instructions="", input=[]))
    assert is_native_compaction_request(_trigger_request())
    ordinary = ResponsesRequest.model_validate(
        {"model": "gpt-6-astra", "instructions": "", "input": _TRIGGER_INPUT[:1]}
    )
    assert not is_native_compaction_request(ordinary)
    assert not is_native_compaction_request(ResponsesRequest(model="gpt-6-astra", instructions="", input=[]))


@pytest.mark.asyncio
async def test_routes_apply_only_to_compaction_requests_and_skip_incompatible_routes(monkeypatch) -> None:
    broken = CompactionRoute("gpt-5.6-sol", "gpt-5.5", None)

    class _Cache:
        async def get(self) -> dict[str, CompactionRoute]:
            return {_LUNA.slug: _LUNA, broken.slug: broken}

    async def _no_windows() -> dict[str, int]:
        return {}

    monkeypatch.setattr(compaction_routes_module, "get_model_compaction_routes_cache", lambda: _Cache())
    monkeypatch.setattr(compaction_routes_module, "get_model_registry", lambda: ModelRegistry(ttl_seconds=60.0))
    monkeypatch.setattr(compaction_routes_module, "effective_client_windows", _no_windows)

    assert await compaction_routes_for(_trigger_request()) == {_LUNA.slug: _LUNA}
    ordinary = ResponsesRequest(model="gpt-6-astra", instructions="", input=[])
    assert await compaction_routes_for(ordinary) == {}


@pytest.mark.parametrize("request_type", ["trigger", "compact"])
@pytest.mark.parametrize("route_effort", ["low", "max"])
def test_compaction_route_rewrites_model_and_effort(request_type: str, route_effort: str) -> None:
    route = CompactionRoute("gpt-6-astra", "gpt-5.6-luna", route_effort)
    payload: ResponsesRequest | ResponsesCompactRequest = (
        _trigger_request()
        if request_type == "trigger"
        else ResponsesCompactRequest.model_validate(
            {"model": "gpt-6-astra", "instructions": "", "input": [], "reasoning": {"effort": "high"}}
        )
    )

    apply_api_key_enforcement(payload, None, compaction_routes={route.slug: route})

    assert payload.model == "gpt-5.6-luna"
    assert payload.reasoning is not None
    assert payload.reasoning.effort == route_effort


def test_route_without_effort_keeps_the_clients_effort() -> None:
    route = CompactionRoute("gpt-6-astra", "gpt-5.6-sol", None)
    payload = _trigger_request(effort="medium")

    apply_api_key_enforcement(payload, _api_key(), compaction_routes={route.slug: route})

    assert payload.model == "gpt-5.6-sol"
    assert payload.reasoning is not None
    assert payload.reasoning.effort == "medium"


def test_route_applies_to_the_api_keys_enforced_model() -> None:
    payload = _trigger_request(model="gpt-5.6-sol")

    apply_api_key_enforcement(payload, _api_key(enforced_model="gpt-6-astra"), compaction_routes={_LUNA.slug: _LUNA})

    assert payload.model == "gpt-5.6-luna"


def test_api_key_enforced_effort_wins_over_the_route_effort() -> None:
    payload = _trigger_request()

    apply_api_key_enforcement(
        payload, _api_key(enforced_reasoning_effort="medium"), compaction_routes={_LUNA.slug: _LUNA}
    )

    assert payload.model == "gpt-5.6-luna"
    assert payload.reasoning is not None
    assert payload.reasoning.effort == "medium"


def test_route_is_skipped_when_the_api_key_does_not_allow_the_compaction_model() -> None:
    payload = _trigger_request()

    apply_api_key_enforcement(payload, _api_key(allowed_models=["gpt-6-astra"]), compaction_routes={_LUNA.slug: _LUNA})

    assert payload.model == "gpt-6-astra"
    assert payload.reasoning is not None
    assert payload.reasoning.effort == "high"


def test_requests_without_routes_are_untouched() -> None:
    payload = _trigger_request()

    apply_api_key_enforcement(payload, None)

    assert payload.model == "gpt-6-astra"
