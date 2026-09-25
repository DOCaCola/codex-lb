from __future__ import annotations

import json

from app.db.models import ModelSourceModel
from app.modules.openrouter.schemas import AccountState, CatalogModel, ModelSelection

_EFFORT_ORDER = ("none", "minimal", "low", "medium", "high", "xhigh", "max", "ultra")


def project_models(state: AccountState) -> list[ModelSourceModel]:
    catalog = {model.id: model for model in state.catalog}
    return [_project(selection, catalog.get(selection.model)) for selection in state.selections]


def _project(selection: ModelSelection, model: CatalogModel | None) -> ModelSourceModel:
    # Retain a disabled routing claim when a selected model disappears. It must
    # never fall through to a subscription account or a different paid model.
    row = ModelSourceModel(
        model=f"openrouter/{selection.model}",
        display_name=selection.display_name or (model.name if model else selection.model),
        is_enabled=model is not None,
        supports_streaming=True,
        supports_tools=False,
        supports_vision=False,
        context_window=selection.context_window,
    )
    metadata: dict[str, object] = {"upstream_model": selection.model}
    if model is not None and model.image is not None:
        metadata["image"] = model.image.model_dump(mode="json")
        metadata["output_modalities"] = model.architecture.output_modalities
        if "text" not in model.architecture.output_modalities:
            row.context_window = None
            row.supports_streaming = model.image.supports_streaming
            row.supports_vision = "image" in model.architecture.input_modalities
            row.raw_metadata_json = json.dumps(metadata)
            return row
    if model is not None:
        assert model.context_length is not None
        metadata["supported_parameters"] = model.supported_parameters
        context_window = min(
            selection.context_window, model.context_length, model.top_provider.context_length or model.context_length
        )
        row.context_window = context_window
        output_limits = [
            value for value in (selection.max_output_tokens, model.top_provider.max_completion_tokens) if value
        ]
        row.max_output_tokens = min(*output_limits, context_window) if output_limits else None
        row.supports_tools = "tools" in model.supported_parameters
        row.supports_vision = "image" in model.architecture.input_modalities
        row.input_per_1m = model.pricing.prompt * 1_000_000 if model.pricing.prompt is not None else None
        row.cached_input_per_1m = (
            model.pricing.input_cache_read * 1_000_000 if model.pricing.input_cache_read is not None else None
        )
        row.output_per_1m = model.pricing.completion * 1_000_000 if model.pricing.completion is not None else None
        metadata["experimental_supported_tools"] = ["custom", "namespace"] if row.supports_tools else []
        metadata["supports_reasoning"] = "reasoning" in model.supported_parameters
        reasoning = model.reasoning
        if reasoning is not None:
            metadata["reasoning_mandatory"] = reasoning.mandatory
            if "supported_efforts" in reasoning.model_fields_set:
                efforts = (
                    reasoning.supported_efforts
                    if reasoning.supported_efforts is not None
                    else ["max", "xhigh", "high", "medium", "low", "minimal", "none"]
                )
                metadata["supported_reasoning_levels"] = sorted(
                    [effort for effort in efforts if not (reasoning.mandatory and effort == "none")],
                    key=lambda effort: _EFFORT_ORDER.index(effort) if effort in _EFFORT_ORDER else len(_EFFORT_ORDER),
                )
            if reasoning.default_effort is not None:
                metadata["default_reasoning_level"] = reasoning.default_effort
    row.raw_metadata_json = json.dumps(metadata)
    return row
