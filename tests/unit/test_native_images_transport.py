import asyncio
import json

import aiohttp
import pytest
from aiohttp import web

from app.core.clients import proxy

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [200, 400, 401, 429, 502, 307])
async def test_native_image_transport_preserves_wire_contract(unused_tcp_port, status):
    calls = []
    body = b'{"created":1,"data":[{"b64_json":"image","generation_id":"native"}]}'

    async def upstream(request):
        calls.append((request.path, await request.read(), dict(request.headers)))
        return web.Response(
            status=status,
            body=body,
            headers={
                "Content-Type": "application/json",
                "Location": "/redirect-target",
                "X-Codex-Imagegen-Request-Id": "native-id",
            },
        )

    app = web.Application()
    app.router.add_route("*", "/{path:.*}", upstream)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "127.0.0.1", unused_tcp_port).start()
    payload = b'{ "model": "gpt-image-2", "prompt": "test", "images": [] }'
    try:
        async with aiohttp.ClientSession() as session:
            response = await proxy.native_image_request(
                "edits",
                payload=payload,
                headers={
                    "content-type": "application/json",
                    "authorization": "Bearer downstream-key",
                    "chatgpt-account-id": "wrong",
                    "x-codex-image-turn-id": "turn",
                },
                access_token="upstream-token",
                account_id="selected-account",
                timeout_seconds=30,
                base_url=f"http://127.0.0.1:{unused_tcp_port}",
                session=session,
            )
        assert isinstance(response, proxy.CodexControlResponse)
        assert response.status_code == status
        assert response.body == body
        assert len(calls) == 1
        path, sent, headers = calls[0]
        assert path == "/codex/images/edits"
        assert sent == payload
        lowered = {key.lower(): value for key, value in headers.items()}
        assert lowered["authorization"] == "Bearer upstream-token"
        assert lowered["chatgpt-account-id"] == "selected-account"
        assert lowered["x-codex-image-turn-id"] == "turn"
    finally:
        await runner.cleanup()


@pytest.mark.asyncio
async def test_native_image_event_stream_is_forwarded_incrementally(unused_tcp_port):
    partial = (
        b'event: image_generation.partial_image\ndata: {"type":"image_generation.partial_image","b64_json":"p"}\n\n'
    )
    completed = b'event: image_generation.completed\ndata: {"type":"image_generation.completed","b64_json":"f"}\n\n'
    release_completed = asyncio.Event()

    async def upstream(request):
        response = web.StreamResponse(headers={"Content-Type": "text/event-stream"})
        await response.prepare(request)
        await response.write(partial)
        await release_completed.wait()
        await response.write(completed)
        await response.write_eof()
        return response

    app = web.Application()
    app.router.add_route("POST", "/codex/images/generations", upstream)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "127.0.0.1", unused_tcp_port).start()
    try:
        async with aiohttp.ClientSession() as session:
            response = await proxy.native_image_request(
                "generations",
                payload=b'{"model":"gpt-image-2","prompt":"test","stream":true}',
                headers={"content-type": "application/json"},
                access_token="upstream-token",
                account_id="selected-account",
                timeout_seconds=30,
                base_url=f"http://127.0.0.1:{unused_tcp_port}",
                session=session,
            )
            assert isinstance(response, proxy.NativeImageStream)
            assert response.status_code == 200
            received = await anext(response.chunks)
            # The partial image arrives before upstream has finished.
            assert received == partial
            release_completed.set()
            async for chunk in response.chunks:
                received += chunk
            assert received == partial + completed
    finally:
        await runner.cleanup()


@pytest.mark.asyncio
async def test_native_image_event_stream_error_status_is_buffered(unused_tcp_port):
    async def upstream(request):
        return web.Response(status=429, body=b'{"error":{"code":"rate_limited"}}', content_type="text/event-stream")

    app = web.Application()
    app.router.add_route("POST", "/codex/images/generations", upstream)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "127.0.0.1", unused_tcp_port).start()
    try:
        async with aiohttp.ClientSession() as session:
            response = await proxy.native_image_request(
                "generations",
                payload=b'{"model":"gpt-image-2","prompt":"test","stream":true}',
                headers={"content-type": "application/json"},
                access_token="upstream-token",
                account_id="selected-account",
                timeout_seconds=30,
                base_url=f"http://127.0.0.1:{unused_tcp_port}",
                session=session,
            )
        assert isinstance(response, proxy.CodexControlResponse)
        assert response.status_code == 429
        assert response.body == b'{"error":{"code":"rate_limited"}}'
    finally:
        await runner.cleanup()


@pytest.mark.asyncio
async def test_native_image_body_limit_stops_reading(monkeypatch):
    monkeypatch.setattr(proxy, "_NATIVE_IMAGE_RESPONSE_MAX_BYTES", 8)

    class Content:
        async def iter_chunked(self, size):
            yield b"12345678"
            yield b"9"
            pytest.fail("must stop at the crossing chunk")

    class Response:
        content = Content()

    with pytest.raises(proxy.ProxyResponseError) as error:
        await proxy._native_image_response_body(Response())
    assert error.value.status_code == 502


@pytest.mark.parametrize(
    "body,expected",
    [
        ({}, (None, None)),
        ({"usage": {"input_tokens": 3, "output_tokens": 7}}, (3, 7)),
        ({"usage": {"input_tokens": "3"}}, (None, None)),
        ({"usage": {"input_tokens": -1}}, (None, None)),
    ],
)
def test_native_usage_is_authoritative_only(body, expected):
    from app.modules.proxy.native_image_usage import reported_image_usage

    usage = reported_image_usage(proxy.CodexControlResponse(200, json.dumps(body).encode(), {}))
    assert (usage.input_tokens, usage.output_tokens) == expected


def _sse(event: str, payload: dict[str, object]) -> bytes:
    return f"event: {event}\ndata: {json.dumps(payload)}\n\n".encode()


def test_stream_observer_reads_usage_across_chunk_boundaries():
    from app.modules.proxy.native_image_usage import NativeImageAccounting, NativeImageStreamObserver

    accounting = NativeImageAccounting(model="gpt-image-2.6-flare")
    observer = NativeImageStreamObserver(accounting)
    stream = _sse("image_generation.partial_image", {"type": "image_generation.partial_image", "b64_json": "x" * 50})
    stream += _sse(
        "image_generation.completed",
        {"type": "image_generation.completed", "b64_json": "y", "usage": {"input_tokens": 4, "output_tokens": 9}},
    )
    for index in range(0, len(stream), 7):
        observer.feed(stream[index : index + 7])
    assert observer.completed
    assert observer.error is None
    assert observer.at_event_boundary
    assert (accounting.usage.input_tokens, accounting.usage.output_tokens) == (4, 9)


def test_stream_observer_records_error_event_and_open_frames():
    from app.modules.proxy.native_image_usage import NativeImageAccounting, NativeImageStreamObserver

    accounting = NativeImageAccounting(model="gpt-image-2")
    observer = NativeImageStreamObserver(accounting)
    observer.feed(b"event: image_generation.partial_image\r\ndata: {")
    assert not observer.at_event_boundary
    observer.feed(b'"type":"image_generation.partial_image"}\r\n\r\n')
    assert observer.at_event_boundary
    observer.feed(_sse("error", {"type": "error", "error": {"code": "moderation_blocked", "message": "no"}}))
    assert observer.error == {"code": "moderation_blocked", "message": "no"}
    assert not observer.completed
    assert accounting.usage.input_tokens is None
