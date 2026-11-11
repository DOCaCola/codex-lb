"""Models the operator hid from client model lists.

Hiding is applied only where client model lists are rendered (the Codex catalog,
the OpenAI-shaped ``/v1/models`` list and the Anthropic models list). The model
registry, routing, API-key authorization and compaction routes never see it, so a
hidden model stays usable by name: Codex keeps resolving its full metadata from
the ``hide`` catalog entry for threads, ``config.toml`` and subagents that name it.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache.dashboard_rows import DashboardRowsCache


class HiddenModelsCache(DashboardRowsCache[frozenset[str]]):
    """Process-wide snapshot of the hidden model slugs."""

    async def _load(self, session: AsyncSession) -> frozenset[str]:
        from app.modules.settings.repository import HiddenModelsRepository

        return await HiddenModelsRepository(session).slugs()


_cache = HiddenModelsCache()


def get_hidden_models_cache() -> HiddenModelsCache:
    return _cache
