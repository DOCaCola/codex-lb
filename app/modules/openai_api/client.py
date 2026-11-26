from __future__ import annotations

import aiohttp
from pydantic import ValidationError

from app.core.clients.http import lease_model_source_session
from app.modules.openai_api.schemas import OPENAI_API_BASE_URL, ModelsResponse, UpstreamModel


class OpenAIApiError(ValueError):
    """Public diagnostics deliberately exclude upstream bodies and credentials."""


class OpenAIApiClient:
    async def models(self, key: str) -> list[UpstreamModel]:
        """``GET /v1/models`` both proves the key and lists the models its project may use."""
        try:
            async with lease_model_source_session() as session:
                async with session.get(
                    OPENAI_API_BASE_URL + "/models",
                    headers={"Authorization": f"Bearer {key}"},
                    timeout=aiohttp.ClientTimeout(total=30, connect=10),
                    allow_redirects=False,
                ) as response:
                    if response.status != 200:
                        raise OpenAIApiError(f"OpenAI /models returned HTTP {response.status}")
                    models = ModelsResponse.model_validate_json(await response.read()).data
        except (aiohttp.ClientError, TimeoutError) as exc:
            raise OpenAIApiError("OpenAI /models could not be reached") from exc
        except ValidationError as exc:
            raise OpenAIApiError("OpenAI /models returned invalid data") from exc
        # An empty list is not evidence that every model went away; keep the served catalog.
        if not models:
            raise OpenAIApiError("OpenAI /models returned an empty model list")
        return models
