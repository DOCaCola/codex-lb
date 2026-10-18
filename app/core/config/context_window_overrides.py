"""Per-model context window overrides: dashboard rows over the environment dict.

``CODEX_LB_MODEL_CONTEXT_WINDOW_OVERRIDES`` (``slug -> window``) is a T3
setting whose dashboard home is the ``model_context_window_overrides`` table
(one row per slug) rather than a ``dashboard_settings`` column, because the
value is a mapping, not a scalar. The precedence of ``configuration-tiers``
still applies per slug: a dashboard row wins, a slug without a row inherits
the environment entry, and a slug with neither has no override (the catalog
reports the upstream window). There is no code default for a slug, so this
module carries its own per-slug resolver instead of ``resolve_inheritable``.

The catalog endpoints (``GET /v1/models``, ``GET /backend-api/codex/models``)
read the dashboard rows through ``ModelContextWindowOverridesCache`` (TTL +
the cross-replica ``settings`` invalidation namespace, like
``SettingsCache``) — never per model entry and never inside a lock.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache.dashboard_rows import DashboardRowsCache

type ContextWindowOverrideSource = Literal["dashboard", "env"]


@dataclass(frozen=True, slots=True)
class ContextWindowOverride:
    """Effective override for one slug and where it came from.

    ``env_value`` is the environment entry for the slug (``None`` when the
    environment has none), reported even while a dashboard row wins so the
    dashboard can show what clearing the row returns to.
    """

    slug: str
    context_window: int
    source: ContextWindowOverrideSource
    env_value: int | None


def resolve_context_window_overrides(
    dashboard: Mapping[str, int], environment: Mapping[str, int]
) -> dict[str, ContextWindowOverride]:
    """Combine dashboard rows and the environment dict, per slug, dashboard first.

    This is the only place that combines the two layers; the catalog and the
    settings API both derive their view from it.
    """
    resolved: dict[str, ContextWindowOverride] = {}
    for slug in sorted(set(dashboard) | set(environment)):
        env_value = environment.get(slug)
        if slug in dashboard:
            resolved[slug] = ContextWindowOverride(slug, dashboard[slug], "dashboard", env_value)
        else:
            assert env_value is not None
            resolved[slug] = ContextWindowOverride(slug, env_value, "env", env_value)
    return resolved


def effective_context_window_overrides(dashboard: Mapping[str, int], environment: Mapping[str, int]) -> dict[str, int]:
    """``slug -> effective window`` (dashboard row, else environment entry)."""
    return {
        slug: override.context_window
        for slug, override in resolve_context_window_overrides(dashboard, environment).items()
    }


class ModelContextWindowOverridesCache(DashboardRowsCache[dict[str, int]]):
    """Process-wide snapshot of the dashboard override rows (``slug -> window``)."""

    async def _load(self, session: AsyncSession) -> dict[str, int]:
        from app.modules.settings.repository import ModelContextWindowOverridesRepository

        return await ModelContextWindowOverridesRepository(session).by_slug()


_cache = ModelContextWindowOverridesCache()


def get_model_context_window_overrides_cache() -> ModelContextWindowOverridesCache:
    return _cache
