from __future__ import annotations

from collections.abc import Collection, Mapping
from contextvars import ContextVar, Token
from dataclasses import dataclass
from enum import StrEnum

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache.dashboard_rows import DashboardRowsCache


@dataclass(frozen=True, slots=True)
class ModelRedirectAttribution:
    requested_model: str
    served_model: str


_request_redirect: ContextVar[ModelRedirectAttribution | None] = ContextVar("request_model_redirect", default=None)


def get_request_model_redirect() -> ModelRedirectAttribution | None:
    return _request_redirect.get()


def set_request_model_redirect(
    attribution: ModelRedirectAttribution | None,
) -> Token[ModelRedirectAttribution | None]:
    return _request_redirect.set(attribution)


def reset_request_model_redirect(token: Token[ModelRedirectAttribution | None]) -> None:
    _request_redirect.reset(token)


class ModelRedirectInactivity(StrEnum):
    TARGET_UNAVAILABLE = "model_redirect_target_unavailable"
    TARGET_REDIRECTED = "model_redirect_target_redirected"


def model_redirect_inactivity(
    target: str,
    redirects: Mapping[str, str],
    catalogue: Collection[str],
) -> ModelRedirectInactivity | None:
    if target in redirects:
        return ModelRedirectInactivity.TARGET_REDIRECTED
    if target not in catalogue:
        return ModelRedirectInactivity.TARGET_UNAVAILABLE
    return None


class ModelRedirectsCache(DashboardRowsCache[dict[str, str]]):
    async def _load(self, session: AsyncSession) -> dict[str, str]:
        from app.modules.settings.repository import ModelRedirectsRepository

        return await ModelRedirectsRepository(session).list_all()


_cache = ModelRedirectsCache()


def get_model_redirects_cache() -> ModelRedirectsCache:
    return _cache
