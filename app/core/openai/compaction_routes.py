"""Native compaction model routes: run a coding model's compaction on another model.

Codex compacts with the model that is coding. A route sends only the upstream
compaction request to another native model, optionally at another effort; the
client keeps its model, so Codex rebuilds the post-compaction context for it.

A route needs both models to share the checkpoint format: the ChatGPT backend
reads a ``compaction`` item from any model with the same ``comp_hash``, and a
compaction model continues the coding model's response through
``previous_response_id`` on the same connection (probed 2026-10-18 with
gpt-6-astra and gpt-6-luna). Codex ignores the server-reported model while
compacting, so the substitution raises no reroute warning.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache.dashboard_rows import DashboardRowsCache
from app.core.config.context_window_overrides import (
    effective_context_window_overrides,
    get_model_context_window_overrides_cache,
)
from app.core.config.settings import get_settings
from app.core.openai.model_registry import (
    MODEL_SOURCE_KIND_SUBSCRIPTION,
    ModelRegistry,
    UpstreamModel,
    get_model_registry,
)
from app.core.openai.requests import ResponsesCompactRequest, ResponsesRequest
from app.core.utils.json_guards import is_json_list, is_json_mapping
from app.core.utils.request_id import get_request_id

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class CompactionRoute:
    slug: str
    compaction_model: str
    reasoning_effort: str | None


class CompactionRouteIncompatibility(StrEnum):
    CODING_MODEL_UNAVAILABLE = "coding_model_unavailable"
    COMPACTION_MODEL_UNAVAILABLE = "compaction_model_unavailable"
    NOTHING_CHANGES = "nothing_changes"
    CHECKPOINT_FORMAT_MISMATCH = "checkpoint_format_mismatch"
    RESPONSES_LITE_MISMATCH = "responses_lite_mismatch"
    CONTEXT_WINDOW_TOO_SMALL = "context_window_too_small"
    INPUT_MODALITIES_MISSING = "input_modalities_missing"
    EFFORT_UNSUPPORTED = "effort_unsupported"
    COMPACTION_MODEL_ROUTED = "compaction_model_routed"


class ModelCompactionRoutesCache(DashboardRowsCache[dict[str, CompactionRoute]]):
    """Process-wide snapshot of the route rows, keyed by coding model."""

    async def _load(self, session: AsyncSession) -> dict[str, CompactionRoute]:
        from app.modules.settings.repository import ModelCompactionRoutesRepository

        return {
            row.slug: CompactionRoute(row.slug, row.compaction_model, row.reasoning_effort)
            for row in await ModelCompactionRoutesRepository(session).list_all()
        }


_cache = ModelCompactionRoutesCache()


def get_model_compaction_routes_cache() -> ModelCompactionRoutesCache:
    return _cache


def native_route_model(registry: ModelRegistry, slug: str) -> UpstreamModel | None:
    """The native catalog entry for ``slug`` while accounts are offered it."""
    model = registry.get_models_with_fallback().get(slug)
    if (
        model is None
        or model.source_kind != MODEL_SOURCE_KIND_SUBSCRIPTION
        or registry.is_suppressed_model(slug)
        or not registry.plan_types_for_model(slug)
    ):
        return None
    return model


def context_ceiling(model: UpstreamModel) -> int:
    """Largest input the backend accepts for ``model``."""
    max_context_window = model.raw.get("max_context_window")
    if isinstance(max_context_window, int) and not isinstance(max_context_window, bool):
        return max(max_context_window, model.context_window)
    return model.context_window


def compaction_route_incompatibility(
    route: CompactionRoute,
    *,
    routes: Mapping[str, CompactionRoute],
    registry: ModelRegistry,
    client_windows: Mapping[str, int],
) -> CompactionRouteIncompatibility | None:
    """Why ``route`` cannot run, or ``None`` when it is compatible.

    ``client_windows`` holds the effective context-window overrides: the
    compaction model must accept the largest history clients send for the
    coding model.
    """
    coding = native_route_model(registry, route.slug)
    if coding is None:
        return CompactionRouteIncompatibility.CODING_MODEL_UNAVAILABLE
    compaction = native_route_model(registry, route.compaction_model)
    if compaction is None:
        return CompactionRouteIncompatibility.COMPACTION_MODEL_UNAVAILABLE
    if route.compaction_model == route.slug and route.reasoning_effort is None:
        return CompactionRouteIncompatibility.NOTHING_CHANGES
    comp_hash = coding.raw.get("comp_hash")
    if not comp_hash or compaction.raw.get("comp_hash") != comp_hash:
        return CompactionRouteIncompatibility.CHECKPOINT_FORMAT_MISMATCH
    if coding.raw.get("use_responses_lite") != compaction.raw.get("use_responses_lite"):
        return CompactionRouteIncompatibility.RESPONSES_LITE_MISMATCH
    if context_ceiling(compaction) < client_windows.get(route.slug, coding.context_window):
        return CompactionRouteIncompatibility.CONTEXT_WINDOW_TOO_SMALL
    if not set(coding.input_modalities) <= set(compaction.input_modalities):
        return CompactionRouteIncompatibility.INPUT_MODALITIES_MISSING
    if route.reasoning_effort is not None and route.reasoning_effort not in {
        level.effort for level in compaction.supported_reasoning_levels
    }:
        return CompactionRouteIncompatibility.EFFORT_UNSUPPORTED
    if route.compaction_model != route.slug and route.compaction_model in routes:
        return CompactionRouteIncompatibility.COMPACTION_MODEL_ROUTED
    return None


async def effective_client_windows() -> dict[str, int]:
    return effective_context_window_overrides(
        await get_model_context_window_overrides_cache().get(),
        get_settings().model_context_window_overrides,
    )


def is_native_compaction_request(payload: ResponsesRequest | ResponsesCompactRequest) -> bool:
    """``/responses/compact``, or Responses input ending in ``compaction_trigger``."""
    if isinstance(payload, ResponsesCompactRequest):
        return True
    items = payload.input
    return (
        is_json_list(items)
        and bool(items)
        and is_json_mapping(items[-1])
        and items[-1].get("type") == "compaction_trigger"
    )


async def compaction_routes_for(payload: ResponsesRequest | ResponsesCompactRequest) -> dict[str, CompactionRoute]:
    """The compatible routes when ``payload`` is a native compaction request, else none.

    API-key enforcement applies the route for the request's effective model.
    """
    if not is_native_compaction_request(payload):
        return {}
    routes = await get_model_compaction_routes_cache().get()
    if not routes:
        return {}
    registry = get_model_registry()
    client_windows = await effective_client_windows()
    active: dict[str, CompactionRoute] = {}
    for route in routes.values():
        reason = compaction_route_incompatibility(
            route, routes=routes, registry=registry, client_windows=client_windows
        )
        if reason is None:
            active[route.slug] = route
        elif route.slug == payload.model:
            logger.warning(
                "compaction_model_route_skipped request_id=%s coding_model=%s compaction_model=%s reason=%s",
                get_request_id(),
                route.slug,
                route.compaction_model,
                reason,
            )
    return active
