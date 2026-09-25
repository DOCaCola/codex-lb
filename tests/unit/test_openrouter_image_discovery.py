from __future__ import annotations

import pytest

from app.modules.openrouter.catalog import project_models
from app.modules.openrouter.client import OpenRouterClient
from app.modules.openrouter.schemas import (
    AccountState,
    CatalogResponse,
    ImageCatalogResponse,
    ModelSelection,
)


@pytest.mark.asyncio
async def test_image_catalog_merges_without_erasing_text_capabilities(monkeypatch):
    text = {
        "id": "vendor/both",
        "name": "Both",
        "context_length": 262144,
        "architecture": {"input_modalities": ["text", "image"], "output_modalities": ["text", "image"]},
        "pricing": {"prompt": "0.000001"},
        "top_provider": {},
        "supported_parameters": ["tools"],
    }
    image = {
        "id": "vendor/both",
        "name": "Both",
        "architecture": {"input_modalities": ["text", "image"], "output_modalities": ["image"]},
        "supports_streaming": True,
        "supported_parameters": {"n": {"type": "range", "min": 1, "max": 10}},
    }
    calls = []

    async def get(self, path, key, schema):
        calls.append((path, key))
        if schema is CatalogResponse:
            return schema.model_validate({"data": [text]})
        assert schema is ImageCatalogResponse
        return schema.model_validate({"data": [image, {**image, "id": "vendor/images"}]})

    monkeypatch.setattr(OpenRouterClient, "_get", get)
    result = await OpenRouterClient().catalog("secret")
    assert calls == [("/models/user", "secret"), ("/images/models", "secret")]
    assert [row.id for row in result.data] == ["vendor/both", "vendor/images"]
    state = AccountState(catalog=result.data, selections=[ModelSelection(model=model.id) for model in result.data])
    both, images = project_models(state)
    assert both.supports_tools
    assert both.context_window == 262144
    assert both.input_per_1m == 1
    assert images.context_window is None
    assert images.input_per_1m is None
    assert not images.supports_tools
