from __future__ import annotations

import asyncio
import contextlib
import json
from collections.abc import AsyncIterator

import aiohttp
import pytest
from aiohttp import web

from app.modules.antigravity import client, oauth
from app.modules.antigravity.errors import AntigravityError
from app.modules.antigravity.version import ClientIdentity

pytestmark = pytest.mark.unit

IDENTITY = ClientIdentity("1.4.10", "123", "darwin_arm64")
CATALOG = json.dumps({"models": {f"model-{index}": {"displayName": "x" * 200} for index in range(200)}}).encode()
TOKEN = json.dumps({"access_token": "access", "expires_in": 3600, "token_type": "Bearer"}).encode()


@pytest.fixture
async def split_upstream(unused_tcp_port, monkeypatch) -> AsyncIterator[dict[str, bytes]]:
    """Answers each path with its body written in two network writes, like a large Google reply."""
    bodies = {"/v1internal:fetchAvailableModels": CATALOG, "/token": TOKEN}

    async def answer(request: web.Request) -> web.StreamResponse:
        payload = bodies[request.path]
        response = web.StreamResponse(headers={"Content-Type": "application/json"})
        await response.prepare(request)
        half = len(payload) // 2
        await response.write(payload[:half])
        await asyncio.sleep(0.05)
        await response.write(payload[half:])
        await response.write_eof()
        return response

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

    for module in (client, oauth):
        monkeypatch.setattr(module, "lease_model_source_session", lease)
    monkeypatch.setattr(client, "CLOUD_CODE_BASE_URL", base)
    monkeypatch.setattr(oauth, "TOKEN_URL", f"{base}/token")
    try:
        yield bodies
    finally:
        await session.close()
        await runner.cleanup()


@pytest.mark.asyncio
async def test_metadata_reply_split_across_reads_is_read_whole(split_upstream) -> None:
    data = await client.CloudCodeClient(IDENTITY).available_models("token", "project-1")
    assert data == json.loads(CATALOG)


@pytest.mark.asyncio
async def test_metadata_reply_over_the_cap_is_rejected(split_upstream, monkeypatch) -> None:
    monkeypatch.setattr(client, "MAX_METADATA_BYTES", len(CATALOG) - 1)
    with pytest.raises(AntigravityError, match="exceeded the size limit"):
        await client.CloudCodeClient(IDENTITY).available_models("token", "project-1")


@pytest.mark.asyncio
async def test_token_reply_split_across_reads_is_read_whole(split_upstream) -> None:
    credentials = await oauth.refresh("refresh")
    assert credentials.access_token.get_secret_value() == "access"
