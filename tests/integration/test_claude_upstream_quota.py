import asyncio
import json
import math
from datetime import UTC, datetime, timedelta

import pytest

from app.modules.claude import transport
from app.modules.model_sources.forwarding import ModelSourceForwardingError
from tests.integration import test_claude_inference as fixtures

MODEL = fixtures.MODEL
pool = fixtures.pool

pytestmark = pytest.mark.integration


def install_rejection(monkeypatch, *, quota=True, deadline=True, utilization=False):
    reset = math.ceil((datetime.now(UTC) + timedelta(hours=2)).timestamp())
    headers = {"anthropic-ratelimit-requests-remaining": "0"}
    if quota:
        headers.update(
            {
                "anthropic-ratelimit-unified-status": "rejected",
                "anthropic-ratelimit-unified-5h-status": "rejected",
                "anthropic-ratelimit-unified-representative-claim": "five_hour",
            }
        )
        if deadline:
            headers["anthropic-ratelimit-unified-5h-reset"] = str(reset)
        if utilization:
            headers["anthropic-ratelimit-unified-5h-utilization"] = "1.0"

    async def reject(*args, **kwargs):
        raise ModelSourceForwardingError(
            status_code=429,
            upstream_status_code=429,
            payload={"error": {"type": "rate_limit_error", "message": "Account rate limit exceeded."}},
            retry_after="12" if deadline else None,
            upstream_headers=headers,
        )

    monkeypatch.setattr(transport, "_open_source_stream", reject)
    return reset


@pytest.mark.parametrize(
    "path,stream",
    [
        ("/v1/responses", True),
        ("/v1/responses", False),
        ("/backend-api/codex/responses", True),
        ("/backend-api/codex/responses", False),
        ("/v1/messages", True),
    ],
)
@pytest.mark.parametrize("quota", [True, False])
async def test_upstream_quota_http_contract(async_client, pool, monkeypatch, path, stream, quota):
    reset = install_rejection(monkeypatch, quota=quota)
    native = path.endswith("messages")
    body = {"model": MODEL, "stream": stream}
    if native:
        body.update(messages=[{"role": "user", "content": "Hello"}], max_tokens=100)
    else:
        body["input"] = "Hello"
    response = await async_client.post(path, json=body)
    assert response.status_code == 429, response.text
    error = response.json()["error"]
    assert error["type"] == ("usage_limit_reached" if quota and not native else "rate_limit_error")
    assert error["message"] == "Account rate limit exceeded."
    assert response.headers["retry-after"] == "12"
    if quota and not native:
        assert error["resets_at"] == reset
        assert 7180 <= error["resets_in_seconds"] <= 7201
    else:
        assert "resets_at" not in error


@pytest.mark.parametrize("path", ["/v1/responses", "/backend-api/codex/responses"])
@pytest.mark.parametrize("quota,deadline", [(True, True), (True, False), (False, True)])
async def test_upstream_quota_websocket_contract(async_client, pool, monkeypatch, path, quota, deadline):
    reset = install_rejection(monkeypatch, quota=quota, deadline=deadline)
    incoming, outgoing = asyncio.Queue(), asyncio.Queue()
    scope = {
        "type": "websocket",
        "asgi": {"version": "3.0"},
        "scheme": "ws",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "root_path": "",
        "headers": [(b"user-agent", b"codex_cli_rs/0.167.0"), (b"session_id", b"quota-rejection")],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
        "subprotocols": [],
    }
    task = asyncio.create_task(async_client._transport.app(scope, incoming.get, outgoing.put))
    try:
        await incoming.put({"type": "websocket.connect"})
        assert (await asyncio.wait_for(outgoing.get(), 5))["type"] == "websocket.accept"
        await incoming.put(
            {
                "type": "websocket.receive",
                "text": json.dumps(
                    {
                        "type": "response.create",
                        "model": MODEL,
                        "input": "Hello",
                    }
                ),
            }
        )
        frame = await asyncio.wait_for(outgoing.get(), 5)
        assert frame["type"] == "websocket.send"
        event = json.loads(frame["text"])
        assert event["type"] == "error" and event["status"] == 429
        error = event["error"]
        assert error["type"] == ("usage_limit_reached" if quota else "rate_limit_error")
        if quota and deadline:
            assert error["resets_at"] == reset
        else:
            assert "resets_at" not in error
    finally:
        await incoming.put({"type": "websocket.disconnect", "code": 1000})
        try:
            await asyncio.wait_for(task, 5)
        finally:
            if not task.done():
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)


async def test_local_quota_refusal_reports_unified_headers_to_native_clients(async_client, pool, monkeypatch):
    reset = install_rejection(monkeypatch, utilization=True)
    body = {"model": MODEL, "stream": True, "messages": [{"role": "user", "content": "Hello"}], "max_tokens": 100}
    first = await async_client.post("/v1/messages", json=body)
    assert first.status_code == 429, first.text
    # The recorded 5h rejection now blocks the pool before any upstream request.
    response = await async_client.post("/v1/messages", json=body)
    assert response.status_code == 429, response.text
    assert response.json()["error"]["code"] == "claude_pool_rate_limited"
    headers = response.headers
    assert headers["anthropic-ratelimit-unified-status"] == "rejected"
    assert "anthropic-ratelimit-unified-overage-status" not in headers
    assert headers["anthropic-ratelimit-unified-representative-claim"] == "five_hour"
    assert headers["anthropic-ratelimit-unified-reset"] == headers["anthropic-ratelimit-unified-5h-reset"] == str(reset)
    assert headers["anthropic-ratelimit-unified-5h-status"] == "rejected"
    assert int(headers["retry-after"]) > 0
