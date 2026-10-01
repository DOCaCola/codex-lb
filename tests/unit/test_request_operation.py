import asyncio

import pytest

from app.core.middleware.path_rewrite import BackendApiCodexV1AliasMiddleware
from app.core.middleware.request_operation import RequestOperationMiddleware, classify_request_operation
from app.core.usage.request_operation import (
    RequestOperation,
    get_request_operation,
    reset_request_operation,
    set_request_operation,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "scope_type,method,path,expected",
    [
        ("http", "POST", "/backend-api/codex/alpha/search", "web_search"),
        ("http", "POST", "/v1/responses/", "responses"),
        ("http", "POST", "/v1/chat/completions", "chat_completions"),
        ("http", "POST", "/v1/messages", "messages"),
        ("http", "POST", "/v1/messages/count_tokens", "count_tokens"),
        ("http", "POST", "/v1/responses/compact", "compaction"),
        ("http", "POST", "/v1/images/generations", "image_generation"),
        ("http", "POST", "/backend-api/codex/images/edits", "image_edit"),
        ("http", "POST", "/v1/audio/transcriptions", "transcription"),
        ("http", "POST", "/backend-api/transcribe", "transcription"),
        ("http", "POST", "/v1/embeddings", "embeddings"),
        ("http", "POST", "/backend-api/files", "file_create"),
        ("http", "POST", "/backend-api/files/file-123/uploaded", "file_finalize"),
        ("http", "GET", "/backend-api/codex/thread/goal/get", "goal_read"),
        ("http", "POST", "/backend-api/codex/thread/goal/set", "goal_set"),
        ("http", "POST", "/backend-api/codex/thread/goal/clear", "goal_clear"),
        ("http", "POST", "/backend-api/codex/memories/trace_summarize", "memory_summary"),
        ("http", "POST", "/backend-api/codex/analytics-events/events", "analytics"),
        ("http", "POST", "/backend-api/codex/safety/arc", "safety"),
        ("http", "GET", "/backend-api/wham/agent-identities/jwks", "identity_keys"),
        ("http", "POST", "/backend-api/codex/realtime/calls", "realtime_call"),
        ("websocket", "GET", "/v1/responses", "responses"),
        ("websocket", "GET", "/backend-api/codex/responses", "responses"),
        ("websocket", "GET", "/v1/realtime", "realtime_session"),
        ("websocket", "GET", "/v1/live/rtc_Example-123", "realtime_session"),
        ("websocket", "GET", "/backend-api/codex/019f219b-dcbd-73f2-8777-6c0e33999e3c", "realtime_session"),
        ("websocket", "GET", "/v1/live/not-a-call-id", "unknown"),
        ("http", "GET", "/backend-api/codex/alpha/search", "unknown"),
        ("http", "GET", "/api/request-logs", "unknown"),
    ],
)
def test_classify_ingress_operation(scope_type, method, path, expected):
    assert classify_request_operation(dict(type=scope_type, method=method, path=path)) == expected


@pytest.mark.asyncio
async def test_operation_scope_isolated_for_concurrent_ingress_and_detached_stream_work():
    observations = []
    tasks = []
    release = asyncio.Event()

    async def detached(path):
        await release.wait()
        observations.append((path, get_request_operation()))

    async def app(scope, receive, send):
        tasks.append(asyncio.create_task(detached(scope["path"])))
        await asyncio.sleep(0)
        assert get_request_operation() == classify_request_operation(scope)

    async def unused():
        return {}

    async def send(_message):
        pass

    middleware = RequestOperationMiddleware(app)
    token = set_request_operation(RequestOperation.EMBEDDINGS)
    try:
        await asyncio.gather(
            middleware(dict(type="http", method="POST", path="/v1/images/edits"), unused, send),
            middleware(dict(type="websocket", path="/v1/responses"), unused, send),
        )
        assert get_request_operation() == RequestOperation.EMBEDDINGS
        release.set()
        await asyncio.gather(*tasks)
    finally:
        reset_request_operation(token)
    assert set(observations) == {
        ("/v1/images/edits", RequestOperation.IMAGE_EDIT),
        ("/v1/responses", RequestOperation.RESPONSES),
    }
    assert get_request_operation() == RequestOperation.UNKNOWN


@pytest.mark.asyncio
async def test_alias_classification_ignores_client_operation_headers_and_resets_on_error():
    seen = []

    async def app(scope, receive, send):
        seen.append(get_request_operation())
        raise RuntimeError("test stream failure")

    async def unused():
        return {}

    async def send(_message):
        pass

    middleware = BackendApiCodexV1AliasMiddleware(RequestOperationMiddleware(app))
    with pytest.raises(RuntimeError, match="test stream failure"):
        await middleware(
            dict(
                type="http",
                method="POST",
                path="/backend-api/codex/v1/alpha/search/",
                headers=[(b"x-codex-bridge-request-operation", b"responses")],
            ),
            unused,
            send,
        )
    assert seen == [RequestOperation.WEB_SEARCH]
    assert get_request_operation() == RequestOperation.UNKNOWN
