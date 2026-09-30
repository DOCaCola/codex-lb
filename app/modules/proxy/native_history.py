"""Authenticated provider history projection for native subscription dispatch."""

from collections.abc import Mapping

from app.core.clients.proxy import ProxyResponseError
from app.core.crypto import TokenEncryptor
from app.core.openai.exceptions import ClientPayloadError
from app.core.openai.requests import ResponsesCompactRequest, ResponsesRequest
from app.modules.api_keys.service import ApiKeyData
from app.modules.claude.opaque import ClaudeOpaqueState
from app.modules.claude.replay import has_claude_replay, project_native_replay
from app.modules.proxy._service.support import _request_log_client_fields
from app.modules.proxy.affinity import _owner_lookup_session_id_from_headers
from app.modules.proxy.request_policy import openai_client_payload_error


def project_native_history[T: ResponsesRequest | ResponsesCompactRequest](
    payload: T,
    headers: Mapping[str, str],
    api_key: ApiKeyData | None,
    *,
    conversation_id: str | None = None,
) -> T:
    items = payload.input
    if not has_claude_replay(items):
        return payload
    assert isinstance(items, list)
    scope = (
        conversation_id
        or _request_log_client_fields(headers)[2]
        or _owner_lookup_session_id_from_headers(headers)
        or "source-responses"
    )
    try:
        projected = project_native_replay(
            items,
            ClaudeOpaqueState(TokenEncryptor()),
            client_scope=api_key.id if api_key else "anonymous",
            conversation_id=scope,
        )
    except ClientPayloadError as exc:
        raise ProxyResponseError(400, openai_client_payload_error(exc)) from exc
    return payload.model_copy(update={"input": projected})
