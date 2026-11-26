"""Provider request projection for model sources whose upstream speaks OpenAI's API directly."""

from __future__ import annotations

from app.core.openai.exceptions import ClientPayloadError
from app.core.types import JsonValue
from app.db.models import ModelSource


def stateless_responses(payload: dict[str, JsonValue]) -> dict[str, JsonValue]:
    """A Responses turn whose history codex-lb retains: the upstream never stores or continues it by ID."""
    if payload.get("previous_response_id") or payload.get("conversation"):
        raise ClientPayloadError(
            "Resend complete history without previous_response_id or conversation",
            param="previous_response_id",
            code="previous_response_not_found",
        )
    projected = dict(payload)
    projected.pop("previous_response_id", None)
    projected.pop("conversation", None)
    projected["store"] = False
    return projected


def project_request(source: ModelSource, payload: dict[str, JsonValue], *, responses: bool) -> dict[str, JsonValue]:
    from app.modules.openai_api import protocol as openai_api
    from app.modules.openai_api.schemas import OPENAI_API_KIND
    from app.modules.openrouter import protocol as openrouter
    from app.modules.openrouter.schemas import OPENROUTER_KIND

    if source.kind == OPENROUTER_KIND:
        return openrouter.project_request(source, payload, responses=responses)
    if source.kind == OPENAI_API_KIND:
        projected = openai_api.project_request(source, payload)
        return stateless_responses(projected) if responses else projected
    return payload
