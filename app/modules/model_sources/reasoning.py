"""Reasoning eligibility for provider-projected source models."""

from pydantic import BaseModel

from app.core.clients.proxy import ProxyResponseError
from app.core.errors import openai_error
from app.core.model_routing import reasoning_allowed
from app.db.models import ModelSource


class SourceReasoningPolicy(BaseModel):
    allowed_reasoning_efforts: list[str] | None = None
    default_reasoning_level: str | None = None


def filter_reasoning_sources(sources: list[ModelSource], model: str, effort: str | None) -> list[ModelSource]:
    eligible = []
    for source in sources:
        row = next(row for row in source.models if row.model == model)
        policy = SourceReasoningPolicy.model_validate_json(row.raw_metadata_json or "{}")
        if reasoning_allowed(policy.allowed_reasoning_efforts, effort, policy.default_reasoning_level):
            eligible.append(source)
    if sources and not eligible:
        error = openai_error(
            "reasoning_effort_not_allowed",
            "No eligible account permits this model's requested or default reasoning effort",
            error_type="invalid_request_error",
        )
        error["error"]["param"] = "reasoning.effort"
        raise ProxyResponseError(400, error)
    return eligible
