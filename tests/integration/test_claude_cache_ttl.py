from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.modules.claude.profile import CLI_IDENTITY
from tests.integration.test_claude_inference import MODEL, install_upstream, native_headers, pool

__all__ = ["pool"]
pytestmark = pytest.mark.integration


@pytest.mark.parametrize("endpoint", ["messages", "messages/count_tokens"])
@pytest.mark.parametrize("native", [False, True])
async def test_wire_cache_order_is_valid_after_projection(async_client, pool, monkeypatch, endpoint, native, caplog):
    from app.modules.claude import transport

    wire = []
    if endpoint.endswith("count_tokens"):

        @asynccontextmanager
        async def post(_url, **kwargs):
            wire.append(kwargs["json"])
            yield SimpleNamespace(status=200, headers={}, json=AsyncMock(return_value={"input_tokens": 42}))

        @asynccontextmanager
        async def lease():
            yield SimpleNamespace(post=post)

        monkeypatch.setattr(transport, "lease_model_source_session", lease)
    else:
        captured, _ = install_upstream(monkeypatch)
    body = {
        "model": MODEL,
        "system": [
            {
                "type": "text",
                "text": CLI_IDENTITY if native else "Caller instructions",
                "cache_control": {"type": "ephemeral", "ttl": "1h"},
            }
        ],
        "messages": [
            {
                "role": "user",
                "content": [{"type": "text", "text": "hello", "cache_control": {"type": "ephemeral"}}],
            }
        ],
    }
    if endpoint == "messages":
        body.update(max_tokens=100, stream=True)
    with caplog.at_level("INFO", logger="app.modules.claude.dispatch"):
        response = await async_client.post(f"/v1/{endpoint}", json=body, headers=native_headers() if native else {})
    assert response.status_code == 200, response.text
    if endpoint == "messages":
        wire.append(captured[0][2])
    assert len(wire) == 1
    sent = wire[0]
    if native:
        assert sent["system"] == body["system"]
        assert sent["messages"] == body["messages"]
        assert "claude_cache_ttl_order_normalized" not in caplog.text
    else:
        assert sent["messages"][0]["content"][0]["cache_control"] == {"type": "ephemeral", "ttl": "1h"}
        assert sent["messages"][1] == {"role": "system", "content": body["system"]}
        assert "claude_cache_ttl_order_normalized" in caplog.text
