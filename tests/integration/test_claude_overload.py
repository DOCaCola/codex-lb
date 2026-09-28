import asyncio
import json

import pytest
from sqlalchemy import select

from app.db.models import ClaudeCooldown
from app.db.session import SessionLocal
from app.modules.claude import transport
from app.modules.model_sources.forwarding import ModelSourceForwardingError
from app.modules.proxy.source_dispatch import SourceDispatch
from tests.integration.test_claude_inference import MODEL, install_upstream
from tests.integration.test_claude_routing import pool as pool

pytestmark = pytest.mark.integration


@pytest.mark.parametrize(
    "status,kind,hint,repeat,sends",
    [
        (529, "overloaded_error", "0", False, 2),
        (503, "overloaded_error", "0", False, 2),
        (503, "api_error", "0", False, 1),
        (529, "overloaded_error", "120", False, 1),
        (529, "overloaded_error", "0", True, 2),
    ],
)
@pytest.mark.parametrize("path", ["/v1/messages", "/v1/responses", "/backend-api/codex/responses"])
async def test_http_overload_policy(async_client, pool, monkeypatch, status, kind, hint, repeat, sends, path):
    captured, closed = install_upstream(monkeypatch)
    original = transport._open_source_stream
    finish = SourceDispatch.finish_with_forwarding_error
    attempts, settled = [], []

    async def settle(self, error):
        await finish(self, error)
        assert self.finished and self._claims_released and self._reservation_done
        settled.append(self.source.id)

    async def send(source, *args, **kwargs):
        if attempts:
            assert settled == [attempts[0]]
        attempts.append(source.id)
        if len(attempts) == 1 or repeat:
            raise ModelSourceForwardingError(
                status_code=status,
                upstream_status_code=status,
                payload={"error": {"type": kind, "message": "busy"}},
                retry_after=hint,
            )
        return await original(source, *args, **kwargs)

    monkeypatch.setattr(SourceDispatch, "finish_with_forwarding_error", settle)
    monkeypatch.setattr(transport, "_open_source_stream", send)
    body = {"model": MODEL, "stream": True}
    body.update(
        {"messages": [{"role": "user", "content": "Hi"}], "max_tokens": 100}
        if path.endswith("messages")
        else {"input": "Hi"}
    )
    response = await async_client.post(path, json=body)
    assert len(attempts) == sends
    assert len(set(attempts)) == 1
    assert len(captured) == len(closed)
    assert response.status_code == (200 if sends == 2 and not repeat else status)
    if response.status_code != 200:
        assert response.headers["retry-after"] == hint
    async with SessionLocal() as session:
        assert list(await session.scalars(select(ClaudeCooldown))) == []


@pytest.mark.parametrize(
    "boundary,retry",
    [
        ("empty", True),
        ("ping", True),
        ("metadata", True),
        ("text", False),
        ("thinking", False),
        ("tool_use", False),
        ("usage", False),
        ("event_limit", False),
        ("byte_limit", False),
        ("malformed", False),
    ],
)
@pytest.mark.parametrize("path", ["/v1/messages", "/v1/responses"])
async def test_sse_overload_boundary(async_client, pool, monkeypatch, boundary, retry, path):
    captured, closed = install_upstream(monkeypatch)
    original = transport._iter_sse_events
    attempts = 0

    async def events(*args):
        nonlocal attempts
        attempts += 1
        if attempts > 1:
            assert len(closed) == 1
            async for frame in original(*args):
                yield frame
            return
        prelude = []
        if boundary == "ping":
            prelude = [{"type": "ping"}]
        elif boundary in {"metadata", "usage", "text", "thinking", "tool_use"}:
            prelude = [
                {
                    "type": "message_start",
                    "message": {
                        "id": "msg_rejected",
                        "usage": {"input_tokens": 10, "output_tokens": int(boundary == "usage")},
                    },
                }
            ]
            if boundary in {"text", "thinking", "tool_use"}:
                prelude.append(
                    {
                        "type": "content_block_start",
                        "index": 0,
                        "content_block": {
                            "type": boundary,
                            "text": "",
                            "thinking": "",
                            "id": "tool_1",
                            "name": captured[0][2]["tools"][0]["name"] if boundary == "tool_use" else "test",
                            "input": {},
                        },
                    }
                )
        elif boundary == "event_limit":
            prelude = [{"type": "ping"}] * 33
        elif boundary == "byte_limit":
            yield ":" + "x" * (64 * 1024) + "\n\n"
        elif boundary == "malformed":
            yield 'data: {"type":"content_block_delta"\n\n'
        for event in prelude:
            yield f"data: {json.dumps(event)}\n\n"
        yield 'data: {"type":"error","error":{"type":"overloaded_error","message":"busy"}}\n\n'

    monkeypatch.setattr(transport, "_iter_sse_events", events)
    body = {"model": MODEL, "stream": True}
    body.update(
        {"messages": [{"role": "user", "content": "Hi"}], "max_tokens": 100}
        if path.endswith("messages")
        else {"input": "Hi"}
    )
    if boundary == "tool_use":
        body["tools"] = [
            {"name": "test", "input_schema": {"type": "object", "properties": {}}}
            if path.endswith("messages")
            else {"type": "function", "name": "test", "parameters": {"type": "object", "properties": {}}}
        ]
    response = await async_client.post(path, json=body)
    assert len(captured) == len(closed) == (2 if retry else 1)
    assert len({call[0] for call in captured}) == 1
    if retry:
        assert response.status_code == 200
        assert "Hello from Claude" in response.text
        assert "msg_rejected" not in response.text
        assert "busy" not in response.text


async def test_stalled_startup_closes_without_retry(async_client, pool, monkeypatch):
    captured, closed = install_upstream(monkeypatch)
    monkeypatch.setattr(transport, "SOURCE_FIRST_FRAME_DEADLINE_SECONDS", 0.01)

    async def events(*args):
        yield 'data: {"type":"ping"}\n\n'
        await asyncio.Event().wait()

    monkeypatch.setattr(transport, "_iter_sse_events", events)
    response = await async_client.post("/v1/responses", json={"model": MODEL, "input": "Hi", "stream": True})
    assert response.status_code == 502
    assert len(captured) == len(closed) == 1
