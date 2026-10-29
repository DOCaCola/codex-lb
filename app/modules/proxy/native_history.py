"""Authenticated provider history projection for native subscription dispatch."""

from app.core.clients.proxy import ProxyResponseError
from app.core.crypto import TokenEncryptor
from app.core.openai.exceptions import ClientPayloadError
from app.core.openai.requests import ResponsesCompactRequest, ResponsesRequest
from app.core.types import JsonValue
from app.modules.antigravity.opaque import has_antigravity_replay, omit_antigravity_replay
from app.modules.api_keys.service import ApiKeyData
from app.modules.claude.opaque import ClaudeOpaqueState
from app.modules.claude.replay import has_claude_replay, project_native_replay
from app.modules.proxy.request_policy import openai_client_payload_error


def has_provider_replay(items: JsonValue) -> bool:
    """Whether history carries Claude or Antigravity state that native dispatch must project first."""
    return has_claude_replay(items) or has_antigravity_replay(items)


def project_native_history[T: ResponsesRequest | ResponsesCompactRequest](
    payload: T,
    api_key: ApiKeyData | None,
) -> T:
    items = payload.input
    if not has_provider_replay(items):
        return payload
    assert isinstance(items, list)
    items = omit_antigravity_replay(items)
    if not has_claude_replay(items):
        return payload.model_copy(update={"input": items})
    try:
        projected = project_native_replay(
            items,
            ClaudeOpaqueState(TokenEncryptor()),
            client_scope=api_key.id if api_key else "anonymous",
        )
    except ClientPayloadError as exc:
        raise ProxyResponseError(400, openai_client_payload_error(exc)) from exc
    return payload.model_copy(update={"input": projected})
