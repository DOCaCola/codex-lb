import json

import pytest

from tests.integration.test_claude_inference import MODEL, install_upstream, pool
from tests.unit.test_claude_search import LOOKUP, search_content

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
    # The profile stub reports each access token as its account UUID.
    assert identity["account_uuid"] == captured[0][3]["authorization"].removeprefix("Bearer ")
    assert captured[0][2]["system"][-1]["cache_control"] == {"type": "ephemeral", "ttl": "1h"}
    assert "extended-cache-ttl-2025-04-11" in captured[0][3]["anthropic-beta"].split(",")


@pytest.mark.parametrize("stream", [False, True])
async def test_live_search_route_replay_and_completed_search_moves(async_client, pool, monkeypatch, stream):
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
    moved = await async_client.post("/v1/responses", json=payload)
    assert moved.status_code == 200, moved.text
    assert len(captured) == 3
    assert captured[2][0] != owner
    sent = json.dumps(captured[2][2]["messages"])
    assert "Web search: test" in sent
    assert "server_tool_use" not in sent
    assert "upstream-owned-opaque-data" not in sent


def recorded_output(response, stream):
    """Items in the order the client records them: done events when streaming."""
    if not stream:
        return response.json()["output"]
    events = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]
    return [event["item"] for event in events if event["type"] == "response.output_item.done"]


@pytest.mark.parametrize("stream", [False, True])
async def test_search_deferred_beside_a_client_call_resumes_on_its_account(async_client, pool, monkeypatch, stream):
    call = search_content()[0]
    tool_use = {"type": "tool_use", "id": "toolu_lookup", "name": "lookup", "input": {}}
    captured, _ = install_upstream(monkeypatch, content=[call, tool_use], stop="tool_use")
    payload = {
        "model": MODEL,
        "input": "Search and look up",
        "stream": stream,
        "tools": [LOOKUP, {"type": "web_search"}],
    }
    response = await async_client.post("/v1/responses", json=payload)
    assert response.status_code == 200, response.text
    output = recorded_output(response, stream)
    assert sorted(item["type"] for item in output) == ["function_call", "reasoning", "web_search_call"]

    resumed, _ = install_upstream(monkeypatch, content=search_content()[1:])
    payload["input"] = [
        {"role": "user", "content": "Search and look up"},
        *output,
        {"type": "function_call_output", "call_id": "toolu_lookup", "output": "found"},
    ]
    again = await async_client.post("/v1/responses", json=payload)
    assert again.status_code == 200, again.text
    assert resumed[0][0] == captured[0][0]
    messages = resumed[0][2]["messages"]
    assert [block["type"] for block in messages[-2]["content"]] == ["server_tool_use", "tool_use"]
    assert [block["type"] for block in messages[-1]["content"]] == ["tool_result"]
    answer = recorded_output(again, stream)
    assert [item["type"] for item in answer] == ["reasoning", "message"]
