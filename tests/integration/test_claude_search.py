import json

import pytest

from tests.integration.test_claude_inference import MODEL, install_upstream, pool
from tests.unit.test_claude_search import search_content

__all__ = ["pool"]
pytestmark = pytest.mark.integration


@pytest.mark.parametrize("path", ["/v1/responses", "/backend-api/codex/responses"])
@pytest.mark.parametrize("stream", [False, True])
async def test_cached_search_allows_normal_route(async_client, pool, monkeypatch, path, stream):
    captured, _ = install_upstream(monkeypatch)
    response = await async_client.post(
        path,
        json={
            "model": MODEL,
            "input": "Hello",
            "stream": stream,
            "tools": [{"type": "web_search", "external_web_access": False}],
        },
    )
    assert response.status_code == 200, response.text
    assert "Hello from Claude" in response.text
    assert "tools" not in captured[0][2]
    identity = json.loads(captured[0][2]["metadata"]["user_id"])
    assert identity["session_id"] == captured[0][3]["x-claude-code-session-id"]
    assert identity["account_uuid"] == ""
    assert captured[0][2]["system"][-1]["cache_control"] == {"type": "ephemeral"}


@pytest.mark.parametrize("stream", [False, True])
async def test_live_search_route_replay_and_unavailable_owner(async_client, pool, monkeypatch, stream):
    captured, _ = install_upstream(monkeypatch, content=search_content())
    payload = {"model": MODEL, "input": "Search", "stream": stream, "tools": [{"type": "web_search"}]}
    response = await async_client.post("/v1/responses", json=payload)
    assert response.status_code == 200, response.text
    if stream:
        events = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]
        result = next(e["response"] for e in events if e["type"] == "response.completed")
    else:
        result = response.json()
    assert result["output"][0]["type"] == "web_search_call"
    owner = captured[0][0]
    # Actual client-style full replay, including the opaque carrier.
    payload["input"] = [
        {"role": "user", "content": "Search"},
        *result["output"],
        {"role": "user", "content": "Continue"},
    ]
    again = await async_client.post("/v1/responses", json=payload)
    assert again.status_code == 200, again.text
    assert captured[1][0] == owner
    blocks = [block for message in captured[1][2]["messages"] for block in message["content"]]
    assert search_content()[0] in blocks and search_content()[1] in blocks
    await async_client.patch(f"/api/claude-accounts/{owner}", json={"isEnabled": False})
    denied = await async_client.post("/v1/responses", json=payload)
    assert denied.status_code != 200
    assert len(captured) == 2
