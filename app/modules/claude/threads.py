"""Native Messages thread operations and request-scoped missing-state recovery."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import JsonValue
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.claude.credentials import ClaudeError
from app.modules.claude.resources import ResourceOriginMissing, ResourceScope, record_keys, resolve_origins
from app.modules.model_sources.forwarding import ModelSourceForwardingError


class ThreadNotFound(ClaudeError):
    code = "thread_not_found"
    status_code = 404

    @property
    def error_type(self) -> str:
        return "not_found_error"


@dataclass(frozen=True)
class MessageThread:
    operation: Literal["create", "continue"]
    previous_message_id: str | None = None

    @classmethod
    def parse(cls, body: dict[str, JsonValue]) -> MessageThread | None:
        if "thread" not in body:
            return None
        thread = body["thread"]
        if not isinstance(thread, dict) or thread.get("type") not in ("create", "continue"):
            raise ClaudeError("Claude thread must specify create or continue")
        if thread["type"] == "create":
            return cls("create")
        identifier = thread.get("previous_message_id")
        if not isinstance(identifier, str) or not identifier.strip():
            raise ClaudeError("Claude thread continuation requires a nonempty previous_message_id")
        return cls("continue", identifier)

    def keys(self, scope: ResourceScope) -> tuple[str, ...]:
        if self.previous_message_id is None:
            return ()
        return scope.keys(frozenset({self.previous_message_id}), kind="message_thread")

    async def owner(self, session: AsyncSession, scope: ResourceScope) -> str | None:
        try:
            return await resolve_origins(session, self.keys(scope))
        except ResourceOriginMissing as exc:
            raise ThreadNotFound(
                "thread_not_found: previous_message_id state is unavailable; resend full history"
            ) from exc


async def record_message(scope: ResourceScope, source_id: str, value: dict[str, JsonValue]) -> None:
    """Record each returned thread message before its ID reaches the caller."""
    message = value.get("message") if value.get("type") == "message_start" else value
    identifier = message.get("id") if isinstance(message, dict) else None
    if not isinstance(identifier, str) or not identifier:
        raise ClaudeError("Claude thread response requires a nonempty message ID")
    await record_keys(scope.keys(frozenset({identifier}), kind="message_thread"), source_id)


def normalize_thread_error(body: dict[str, JsonValue], error: ModelSourceForwardingError) -> ModelSourceForwardingError:
    thread = MessageThread.parse(body)
    if thread is None or thread.operation != "continue" or error.upstream_status_code != 404:
        return error
    detail = error.payload.get("error")
    if not isinstance(detail, dict):
        return error
    message = detail.get("message")
    details = detail.get("details")
    missing = (
        detail.get("type") == "thread_not_found"
        or detail.get("code") == "thread_not_found"
        or isinstance(details, dict)
        and details.get("error_code") == "thread_not_found"
        or isinstance(message, str)
        and "No thread state was found" in message
        and "previous_message_id" in message
    )
    if not missing:
        return error
    text = message if isinstance(message, str) else "Previous message thread state was not found"
    if "thread_not_found" not in text:
        text = "thread_not_found: " + text
    return ModelSourceForwardingError(
        status_code=404,
        upstream_status_code=404,
        payload={
            "type": "error",
            "error": {
                **detail,
                "type": "not_found_error",
                "code": "thread_not_found",
                "message": text,
                "details": {**(details if isinstance(details, dict) else {}), "error_code": "thread_not_found"},
            },
        },
        upstream_headers=error.upstream_headers,
    )
