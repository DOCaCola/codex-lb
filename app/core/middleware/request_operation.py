"""Retain canonical ingress operations through streams and detached tasks."""

import re

from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.clients.proxy_websocket import REALTIME_LIVE_CALL_ID_ROUTE_REGEX
from app.core.usage.request_operation import RequestOperation, reset_request_operation, set_request_operation

_POST_OPERATIONS = {
    "responses": RequestOperation.RESPONSES,
    "responses/compact": RequestOperation.COMPACTION,
    "chat/completions": RequestOperation.CHAT_COMPLETIONS,
    "messages": RequestOperation.MESSAGES,
    "messages/count_tokens": RequestOperation.COUNT_TOKENS,
    "images/generations": RequestOperation.IMAGE_GENERATION,
    "images/edits": RequestOperation.IMAGE_EDIT,
    "audio/transcriptions": RequestOperation.TRANSCRIPTION,
    "embeddings": RequestOperation.EMBEDDINGS,
    "alpha/search": RequestOperation.WEB_SEARCH,
    "thread/goal/get": RequestOperation.GOAL_READ,
    "thread/goal/set": RequestOperation.GOAL_SET,
    "thread/goal/clear": RequestOperation.GOAL_CLEAR,
    "memories/trace_summarize": RequestOperation.MEMORY_SUMMARY,
    "analytics-events/events": RequestOperation.ANALYTICS,
    "safety/arc": RequestOperation.SAFETY,
    "realtime/calls": RequestOperation.REALTIME_CALL,
}
_LIVE_PATH = re.compile(rf"(?:/v1/live/|/backend-api/codex/){REALTIME_LIVE_CALL_ID_ROUTE_REGEX}\Z")
_FINALIZE_PATH = re.compile(r"/backend-api/files/[^/]+/uploaded\Z")


def classify_request_operation(scope: Scope) -> RequestOperation:
    path = scope["path"].rstrip("/")
    if scope["type"] == "websocket":
        if path in {"/v1/responses", "/backend-api/codex/responses"}:
            return RequestOperation.RESPONSES
        if path == "/v1/realtime" or _LIVE_PATH.fullmatch(path):
            return RequestOperation.REALTIME_SESSION
        return RequestOperation.UNKNOWN
    method = scope["method"]
    if method == "POST":
        if path == "/backend-api/transcribe":
            return RequestOperation.TRANSCRIPTION
        if path == "/backend-api/files":
            return RequestOperation.FILE_CREATE
        if _FINALIZE_PATH.fullmatch(path):
            return RequestOperation.FILE_FINALIZE
    for prefix in ("/backend-api/codex/", "/v1/"):
        if path.startswith(prefix):
            endpoint = path[len(prefix) :]
            if method == "POST":
                return _POST_OPERATIONS.get(endpoint, RequestOperation.UNKNOWN)
            if method == "GET" and endpoint == "thread/goal/get":
                return RequestOperation.GOAL_READ
            if method == "GET" and endpoint == "agent-identities/jwks":
                return RequestOperation.IDENTITY_KEYS
    if method == "GET" and path == "/backend-api/wham/agent-identities/jwks":
        return RequestOperation.IDENTITY_KEYS
    return RequestOperation.UNKNOWN


class RequestOperationMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in {"http", "websocket"}:
            await self.app(scope, receive, send)
            return
        token = set_request_operation(classify_request_operation(scope))
        try:
            await self.app(scope, receive, send)
        finally:
            reset_request_operation(token)
