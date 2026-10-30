from __future__ import annotations

import contextlib
from collections.abc import AsyncIterator

import aiohttp
import pytest
from aiohttp import web

from app.db.models import ModelSource
from app.modules.antigravity import client, oauth
from app.modules.antigravity.constants import GO_SKIP_AUTO_HEADERS
from app.modules.antigravity.version import ClientIdentity
from app.modules.model_sources import forwarding

pytestmark = pytest.mark.unit

IDENTITY = ClientIdentity("1.4.10", "123", "darwin_arm64")
TOKEN = b'{"access_token":"access","expires_in":3600,"refresh_token":"refresh","token_type":"Bearer"}'
CLI_HEADERS = {"host", "user-agent", "authorization", "content-type", "accept-encoding", "content-length"}


@pytest.fixture
async def upstream(unused_tcp_port, monkeypatch) -> AsyncIterator[tuple[str, list[dict[str, str]]]]:
    """A local Cloud Code / Google OAuth stand-in recording each request's headers as sent."""
    received: list[dict[str, str]] = []

    async def answer(request: web.Request) -> web.Response:
        received.append(dict(request.headers))
        body = TOKEN if request.path == "/token" else b'{"ok":true}'
        return web.Response(body=body, content_type="application/json")

    app = web.Application()
    app.router.add_route("*", "/{path:.*}", answer)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "127.0.0.1", unused_tcp_port).start()
    base = f"http://127.0.0.1:{unused_tcp_port}"
    session = aiohttp.ClientSession()

    @contextlib.asynccontextmanager
    async def lease() -> AsyncIterator[aiohttp.ClientSession]:
        yield session

    for module in (client, oauth, forwarding):
        monkeypatch.setattr(module, "lease_model_source_session", lease)
    monkeypatch.setattr(client, "CLOUD_CODE_BASE_URL", base)
    monkeypatch.setattr(oauth, "TOKEN_URL", f"{base}/token")
    try:
        yield base, received
    finally:
        await session.close()
        await runner.cleanup()


def _names(headers: dict[str, str]) -> set[str]:
    return {name.lower() for name in headers}


@pytest.mark.asyncio
async def test_cloud_code_calls_carry_only_the_cli_headers(upstream) -> None:
    _, received = upstream
    await client.CloudCodeClient(IDENTITY).call("loadCodeAssist", "token", {"metadata": {}})
    (headers,) = received
    assert _names(headers) == CLI_HEADERS


@pytest.mark.asyncio
async def test_token_refresh_sends_no_accept_header(upstream) -> None:
    _, received = upstream
    await oauth.refresh("refresh")
    (headers,) = received
    assert "accept" not in _names(headers)
    assert headers["User-Agent"] == oauth.GO_USER_AGENT


@pytest.mark.asyncio
async def test_prepared_stream_carries_only_the_cli_headers(upstream) -> None:
    base, received = upstream
    source = ModelSource(id="src-1", name="Antigravity", kind="antigravity", base_url=base)
    stack, response, _ = await forwarding._open_source_stream(
        source,
        "/v1internal:streamGenerateContent?alt=sse",
        {"request": {}},
        encryptor=None,
        prepared_headers=client.native_headers("token", IDENTITY),
        skip_auto_headers=GO_SKIP_AUTO_HEADERS,
        first_frame_deadline_seconds=None,
        compact_json=True,
    )
    await stack.aclose()
    assert response.status == 200
    (headers,) = received
    assert _names(headers) == CLI_HEADERS
