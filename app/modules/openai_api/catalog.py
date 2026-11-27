from __future__ import annotations

import json

from app.core.openai.model_registry import get_model_registry
from app.db.models import ModelSourceModel
from app.modules.openai_api.schemas import (
    OPENAI_API_MODEL_PREFIX,
    AccountState,
    CatalogModel,
    ModelKind,
    UpstreamModel,
)

# Families that do not answer Responses or Chat Completions.
_NON_CONVERSATION_MARKERS = (
    "embedding",
    "tts",
    "whisper",
    "transcribe",
    "moderation",
    "realtime",
    "audio",
    "davinci",
    "babbage",
    "instruct",
    "sora",
    "dall-e",
)
# Image models that accept the JSON Images body the native image route builds.
_IMAGE_PREFIXES = ("gpt-image-", "chatgpt-image-")
# OpenAI's own Responses API runs its hosted tools; declare them so source projection keeps them.
_RESPONSES_TOOL_TYPES = [
    "custom",
    "web_search",
    "web_search_preview",
    "file_search",
    "code_interpreter",
    "image_generation",
    "mcp",
    "computer_use_preview",
    "local_shell",
    "shell",
    "apply_patch",
]


def model_kind(model_id: str) -> ModelKind | None:
    if model_id.startswith(_IMAGE_PREFIXES):
        return "image"
    if any(marker in model_id for marker in _NON_CONVERSATION_MARKERS):
        return None
    return "text"


def catalog_models(models: list[UpstreamModel]) -> list[CatalogModel]:
    catalog = [
        CatalogModel(id=model.id, kind=kind, created=model.created)
        for model in models
        if (kind := model_kind(model.id)) is not None
    ]
    return sorted(catalog, key=lambda model: (model.kind, model.id))


def project_models(state: AccountState) -> list[ModelSourceModel]:
    catalog = {model.id: model for model in state.catalog}
    return [
        _project(selection.model, selection.display_name, catalog.get(selection.model))
        for selection in state.selections
    ]


def publishable_text_models(state: AccountState) -> dict[str, str]:
    """Every text catalog model under its published slug, enabled or not."""
    return {OPENAI_API_MODEL_PREFIX + model.id: model.id for model in state.catalog if model.kind == "text"}


def _project(model_id: str, display_name: str | None, model: CatalogModel | None) -> ModelSourceModel:
    # A selected model that left the catalog keeps a disabled routing claim, so it never falls
    # through to a subscription account or another model.
    row = ModelSourceModel(
        model=OPENAI_API_MODEL_PREFIX + model_id,
        display_name=display_name or model_id,
        is_enabled=model is not None,
        supports_streaming=True,
        supports_tools=False,
        supports_vision=False,
    )
    metadata: dict[str, object] = {"upstream_model": model_id}
    if model is not None and model.kind == "image":
        metadata["image"] = {"id": model_id}
        metadata["output_modalities"] = ["image"]
        row.supports_vision = True
        row.raw_metadata_json = json.dumps(metadata)
        return row
    row.supports_tools = True
    metadata["experimental_supported_tools"] = _RESPONSES_TOOL_TYPES
    known = get_model_registry().get_models_with_fallback().get(model_id)
    if known is None:
        # The native registry describes OpenAI's models; an id it does not know keeps the source defaults.
        metadata["default_reasoning_level"] = "none"
    else:
        row.context_window = known.context_window
        row.supports_vision = "image" in known.input_modalities
        max_output_tokens = known.raw.get("max_output_tokens")
        if isinstance(max_output_tokens, int):
            row.max_output_tokens = max_output_tokens
        efforts = [level.effort for level in known.supported_reasoning_levels]
        metadata["supports_reasoning"] = bool(efforts)
        metadata["supported_reasoning_levels"] = efforts
        if known.default_reasoning_level is not None:
            metadata["default_reasoning_level"] = known.default_reasoning_level
        metadata["supports_reasoning_summaries"] = known.supports_reasoning_summaries
    row.raw_metadata_json = json.dumps(metadata)
    return row
