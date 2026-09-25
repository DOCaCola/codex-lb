from __future__ import annotations

from typing import TypeVar

import aiohttp
from pydantic import BaseModel, ValidationError

from app.core.clients.http import lease_model_source_session
from app.modules.openrouter.schemas import (
    OPENROUTER_BASE_URL,
    CatalogResponse,
    CreditInfo,
    CreditResponse,
    KeyInfo,
    KeyResponse,
)

T = TypeVar("T", bound=BaseModel)


class OpenRouterError(ValueError):
    """Public diagnostics deliberately exclude upstream bodies and credentials."""


class OpenRouterClient:
    async def _get(self, path: str, key: str, schema: type[T]) -> T:
        try:
            async with lease_model_source_session() as session:
                async with session.get(
                    OPENROUTER_BASE_URL + path,
                    headers={"Authorization": f"Bearer {key}"},
                    timeout=aiohttp.ClientTimeout(total=30, connect=10),
                    allow_redirects=False,
                ) as response:
                    if response.status != 200:
                        raise OpenRouterError(f"OpenRouter {path} returned HTTP {response.status}")
                    return schema.model_validate_json(await response.read())
        except (aiohttp.ClientError, TimeoutError) as exc:
            raise OpenRouterError(f"OpenRouter {path} could not be reached") from exc
        except ValidationError as exc:
            raise OpenRouterError(f"OpenRouter {path} returned invalid data") from exc

    async def key_info(self, key: str) -> KeyInfo:
        return (await self._get("/key", key, KeyResponse)).data

    async def catalog(self, key: str) -> CatalogResponse:
        # No pagination parameters: OpenRouter returns the full filtered catalog.
        return await self._get("/models/user", key, CatalogResponse)

    async def credits(self, key: str) -> CreditInfo:
        return (await self._get("/credits", key, CreditResponse)).data
