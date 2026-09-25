from __future__ import annotations

import json

from app.core.openai.exceptions import ClientPayloadError
from app.core.types import JsonValue
from app.db.models import ModelSource
from app.modules.openrouter.schemas import OPENROUTER_KIND


def project_request(source: ModelSource, payload: dict[str, JsonValue], *, responses: bool) -> dict[str, JsonValue]:
    if source.kind != OPENROUTER_KIND:
        return payload
    model = next((row for row in source.models if row.model == payload.get("model")), None)
    if model is None:
        raise ClientPayloadError("OpenRouter model is not configured", param="model", code="model_not_found")
    metadata = json.loads(model.raw_metadata_json or "{}")
    upstream_model = metadata["upstream_model"]
    projected = {**payload, "model": upstream_model}
    if responses:
        if projected.get("previous_response_id") or projected.get("conversation"):
            raise ClientPayloadError(
                "Resend complete history without previous_response_id or conversation",
                param="previous_response_id",
                code="previous_response_not_found",
            )
        projected.pop("previous_response_id", None)
        projected.pop("conversation", None)
        projected["store"] = False
    reasoning = projected.get("reasoning")
    if metadata.get("reasoning_mandatory") and isinstance(reasoning, dict):
        if reasoning.get("effort") == "none" or reasoning.get("enabled") is False:
            raise ClientPayloadError("This model requires reasoning", param="reasoning", code="unsupported_parameter")
    # Explicit price-first routing preserves the operator's cost preference.
    # User-supplied routing constraints stay intact; model fallback is not added.
    provider = projected.get("provider")
    if provider is None:
        projected["provider"] = {"sort": "price", "require_parameters": True}
    return projected
