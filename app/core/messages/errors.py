"""Anthropic error envelopes for Messages requests served by Responses models."""

from __future__ import annotations

from collections.abc import Mapping

from app.core.types import JsonValue

_PROMPT_TOO_LONG = "prompt is too long"
_OVERFLOW_CODES = frozenset({"context_length_exceeded"})
_OVERFLOW_MARKERS = (
    _PROMPT_TOO_LONG,
    "context window",
    "context length",
    "maximum context length",
    "input token limit",
)
_RATE_LIMIT_CODES = frozenset({"rate_limit_exceeded", "usage_limit_reached", "insufficient_quota"})
_AUTHENTICATION_CODES = frozenset({"invalid_api_key", "invalid_authentication", "token_invalidated"})
_NOT_FOUND_CODES = frozenset({"not_found", "model_not_found"})


class MessagesRequestError(ValueError):
    """A Messages request that cannot be expressed as a Responses request."""


def anthropic_error_body(error_type: str, message: str) -> dict[str, JsonValue]:
    return {"type": "error", "error": {"type": error_type, "message": message}}


def anthropic_error(status: int, error: Mapping[str, JsonValue] | None) -> tuple[int, dict[str, JsonValue]]:
    """Map an OpenAI-shaped error to the Anthropic status and envelope Claude Code acts on.

    Context overflow becomes 400 "prompt is too long" so Claude Code compacts reactively.
    """
    code = _text(error, "code")
    error_type = _text(error, "type")
    message = _text(error, "message") or "Upstream request failed"
    lowered = message.lower()
    if code in _OVERFLOW_CODES or any(marker in lowered for marker in _OVERFLOW_MARKERS):
        detail = message if lowered.startswith(_PROMPT_TOO_LONG) else f"{_PROMPT_TOO_LONG}: {message}"
        return 400, anthropic_error_body("invalid_request_error", detail)
    if status == 429 or code in _RATE_LIMIT_CODES or error_type == "rate_limit_error":
        return 429, anthropic_error_body("rate_limit_error", message)
    if status == 529 or code == "server_is_overloaded":
        return 529, anthropic_error_body("overloaded_error", message)
    if status == 401 or code in _AUTHENTICATION_CODES or error_type == "authentication_error":
        return 401, anthropic_error_body("authentication_error", message)
    if status == 403 or error_type == "permission_error":
        return 403, anthropic_error_body("permission_error", message)
    if status == 404 or code in _NOT_FOUND_CODES:
        return 404, anthropic_error_body("not_found_error", message)
    if 400 <= status < 500 or error_type == "invalid_request_error":
        return (status if 400 <= status < 500 else 400), anthropic_error_body("invalid_request_error", message)
    return (status if status >= 500 else 502), anthropic_error_body("api_error", message)


def _text(error: Mapping[str, JsonValue] | None, key: str) -> str | None:
    if error is None:
        return None
    value = error.get(key)
    return value if isinstance(value, str) and value else None
