"""Request-state side of rejected encrypted-content recovery.

The WebSocket and HTTP bridge surfaces keep a request's serialized
``response.create`` body (``request_text``) and, for an anchored request, the
retained full-history body (``fresh_upstream_request_text``). When upstream
explicitly refuses replayed ciphertext, the ciphertext the sent body carried is
remembered (``app.core.openai.encrypted_content``) and both bodies lose it
before the single replay. The operation comes from the request state: these
helpers run in the upstream reader, outside the request task.
"""

from __future__ import annotations

from app.core.openai.encrypted_content import (
    encrypted_content_recovery_applies,
    is_encrypted_content_rejection,
    remember_rejected_encrypted_content_text,
    strip_rejected_encrypted_content_text,
)
from app.modules.proxy._service.support import _WebSocketRequestState


def request_state_encrypted_content_rejection(
    request_state: _WebSocketRequestState,
    *,
    error_code: str | None,
    error_message: str | None,
) -> bool:
    """Return whether this terminal refuses ciphertext the request may recover from."""
    return encrypted_content_recovery_applies(request_state.request_operation) and is_encrypted_content_rejection(
        error_code, error_message
    )


def remember_request_state_rejected_encrypted_content(
    request_state: _WebSocketRequestState,
    *,
    error_code: str | None,
    error_message: str | None,
) -> int:
    """Remember the ciphertext of an explicitly refused body; return the new digest count."""
    if not request_state_encrypted_content_rejection(
        request_state,
        error_code=error_code,
        error_message=error_message,
    ):
        return 0
    return remember_rejected_encrypted_content_text(request_state.request_text, request_state.request_operation)


def strip_request_state_rejected_encrypted_content(request_state: _WebSocketRequestState) -> bool:
    """Remove refused ciphertext from the bodies a replay may send.

    Returns whether the sent body carried any; only then does a replay differ
    from the request upstream refused.
    """
    operation = request_state.request_operation
    stripped_request_text = strip_rejected_encrypted_content_text(request_state.request_text, operation)
    if stripped_request_text is None:
        return False
    request_state.request_text = stripped_request_text
    stripped_fresh_text = strip_rejected_encrypted_content_text(request_state.fresh_upstream_request_text, operation)
    if stripped_fresh_text is not None:
        request_state.fresh_upstream_request_text = stripped_fresh_text
    return True
