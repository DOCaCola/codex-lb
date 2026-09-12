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
            response = await proxy.codex_control_request(
                "images/edits",
                method="POST",
                payload=payload,
                query_params={},
                headers={
                    "content-type": "application/json",
                    "authorization": "Bearer downstream-key",
                    "chatgpt-account-id": "wrong",
                    "x-codex-image-turn-id": "turn",
                },
                access_token="upstream-token",
                account_id="selected-account",
                base_url=f"http://127.0.0.1:{unused_tcp_port}",
                session=session,
            )
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
async def test_native_image_body_limit_closes_stream(monkeypatch):
    monkeypatch.setattr(proxy, "_NATIVE_IMAGE_RESPONSE_MAX_BYTES", 8)

    class Content:
        async def iter_chunked(self, size):
            yield b"12345678"
            yield b"9"
            pytest.fail("must stop at the crossing chunk")

    class Response:
        content = Content()
        released = False

        def release(self):
            self.released = True

    response = Response()
    with pytest.raises(proxy.ProxyResponseError) as error:
        await proxy._native_image_response_body(response)
    assert error.value.status_code == 502
    assert response.released


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
