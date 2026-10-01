"""Authenticated provider history projection for native subscription dispatch."""

from app.core.clients.proxy import ProxyResponseError
from app.core.crypto import TokenEncryptor
from app.core.openai.exceptions import ClientPayloadError
from app.core.openai.requests import ResponsesCompactRequest, ResponsesRequest
from app.modules.api_keys.service import ApiKeyData
from app.modules.claude.opaque import ClaudeOpaqueState
from app.modules.claude.replay import has_claude_replay, project_native_replay
from app.modules.proxy.request_policy import openai_client_payload_error


def project_native_history[T: ResponsesRequest | ResponsesCompactRequest](
    payload: T,
    api_key: ApiKeyData | None,
) -> T:
    items = payload.input
    if not has_claude_replay(items):
        return payload
    assert isinstance(items, list)
    try:
        projected = project_native_replay(
            items,
            ClaudeOpaqueState(TokenEncryptor()),
            client_scope=api_key.id if api_key else "anonymous",
        )
    except ClientPayloadError as exc:
        raise ProxyResponseError(400, openai_client_payload_error(exc)) from exc
    return payload.model_copy(update={"input": projected})
