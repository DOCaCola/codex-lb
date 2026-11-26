from __future__ import annotations

import json

from app.core.openai.exceptions import ClientPayloadError
from app.core.types import JsonValue
from app.db.models import ModelSource


def project_request(source: ModelSource, payload: dict[str, JsonValue]) -> dict[str, JsonValue]:
    model = next((row for row in source.models if row.model == payload.get("model")), None)
    if model is None:
        raise ClientPayloadError("OpenAI API model is not configured", param="model", code="model_not_found")
    metadata = json.loads(model.raw_metadata_json or "{}")
    if "image" in metadata:
        raise ClientPayloadError("Use /v1/images for this image model", param="model", code="unsupported_model")
    return {**payload, "model": metadata["upstream_model"]}
