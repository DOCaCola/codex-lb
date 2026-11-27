"""The operator's model names.

A name replaces the provider-supplied display name wherever a model is presented: the Codex
catalog, the OpenAI-shaped ``/v1/models`` list, the Anthropic models list and the dashboard.
Routing, request bodies and the identity a routed model is told about keep the provider's name.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import replace

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache.dashboard_rows import DashboardRowsCache
from app.core.openai.model_registry import UpstreamModel


class ModelDisplayNamesCache(DashboardRowsCache[Mapping[str, str]]):
    """Process-wide snapshot of ``slug -> name``."""

    async def _load(self, session: AsyncSession) -> Mapping[str, str]:
        from app.modules.settings.repository import ModelDisplayNamesRepository

        return await ModelDisplayNamesRepository(session).by_slug()


_cache = ModelDisplayNamesCache()


def get_model_display_names_cache() -> ModelDisplayNamesCache:
    return _cache


def named(model: UpstreamModel, names: Mapping[str, str]) -> UpstreamModel:
    """``model`` presented under the operator's name for its slug, if one is set."""
    name = names.get(model.slug)
    return model if name is None else replace(model, display_name=name)


def named_models(models: Iterable[UpstreamModel], names: Mapping[str, str]) -> list[UpstreamModel]:
    return [named(model, names) for model in models]


def named_by_slug(models: Mapping[str, UpstreamModel], names: Mapping[str, str]) -> dict[str, UpstreamModel]:
    return {slug: named(model, names) for slug, model in models.items()}
