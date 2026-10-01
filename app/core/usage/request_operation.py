"""Server-owned ingress operation, independent of accounting workload kind."""

from contextvars import ContextVar, Token
from enum import StrEnum


class RequestOperation(StrEnum):
    UNKNOWN = "unknown"
    RESPONSES = "responses"
    CHAT_COMPLETIONS = "chat_completions"
    MESSAGES = "messages"
    COUNT_TOKENS = "count_tokens"
    COMPACTION = "compaction"
    CHECKPOINT_HANDOFF = "checkpoint_handoff"
    IMAGE_GENERATION = "image_generation"
    IMAGE_EDIT = "image_edit"
    TRANSCRIPTION = "transcription"
    EMBEDDINGS = "embeddings"
    FILE_CREATE = "file_create"
    FILE_FINALIZE = "file_finalize"
    WEB_SEARCH = "web_search"
    GOAL_READ = "goal_read"
    GOAL_SET = "goal_set"
    GOAL_CLEAR = "goal_clear"
    MEMORY_SUMMARY = "memory_summary"
    ANALYTICS = "analytics"
    SAFETY = "safety"
    IDENTITY_KEYS = "identity_keys"
    REALTIME_CALL = "realtime_call"
    REALTIME_SESSION = "realtime_session"


_OPERATION: ContextVar[RequestOperation] = ContextVar("request_operation", default=RequestOperation.UNKNOWN)


def get_request_operation() -> RequestOperation:
    return _OPERATION.get()


def set_request_operation(value: RequestOperation) -> Token[RequestOperation]:
    return _OPERATION.set(value)


def reset_request_operation(token: Token[RequestOperation]) -> None:
    _OPERATION.reset(token)


def refine_responses_operation(operation: RequestOperation, *, terminal_compaction: bool) -> RequestOperation:
    """Refine an ingress label from an already validated routing decision."""
    if operation == RequestOperation.RESPONSES and terminal_compaction:
        return RequestOperation.COMPACTION
    return operation
