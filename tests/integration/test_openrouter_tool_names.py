import json
import re

import pytest
from aiohttp import web
from sqlalchemy import select

from app.core.utils.sse import parse_sse_data_json
from app.db.models import ModelSource, RequestLog
from app.db.session import SessionLocal
from tests.integration.model_source_helpers import stub_source_upstreams
from tests.integration.test_openrouter_accounts import provider

__all__ = ["provider"]
pytestmark = pytest.mark.integration


@pytest.mark.parametrize("path", ["/v1/responses", "/backend-api/codex/responses", "/v1/chat/completions"])
@pytest.mark.parametrize("stream", [False, True])
async def test_public_tool_names_roundtrip(async_client, provider, path, stream):
    chat = path.endswith("chat/completions")
    name = "mcp__codex_apps__" + "document_" * 8 + "execute"
    calls = []

    async def upstream(request):
        body = await request.json()
        calls.append(body)
        tool = body["tools"][0]
        alias = tool["function"]["name"] if chat else tool["name"]
        assert re.fullmatch(r"[A-Za-z0-9_-]{1,64}", alias)
        assert alias != name
        selected = body["tool_choice"]["function"]["name"] if chat else body["tool_choice"]["name"]
        assert selected == alias
        if chat:
            function = {"name": alias, "arguments": '{"text":"unchanged"}'}
            tool_call = {"id": "call_one", "type": "function", "function": function}
            result = {
                "id": "chat_test",
                "object": "chat.completion",
                "model": "vendor/test",
                "created": 0,
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": None, "tool_calls": [tool_call]},
                        "finish_reason": "tool_calls",
                    }
                ],
                "usage": {"prompt_tokens": 10, "completion_tokens": 2, "total_tokens": 12},
            }
            chunk = {
                **result,
                "object": "chat.completion.chunk",
                "choices": [
                    {
                        "index": 0,
                        "delta": {"role": "assistant", "tool_calls": [{"index": 0, **tool_call}]},
                        "finish_reason": "tool_calls",
                    }
                ],
            }
            events = [chunk]
        else:
            item = {
                "type": "function_call",
                "id": "fc_one",
                "call_id": "call_one",
                "name": alias,
                "arguments": '{"text":"unchanged"}',
                "status": "completed",
            }
            result = {
                "id": "resp_test",
                "object": "response",
                "model": "vendor/test",
                "status": "completed",
                "output": [item],
                "usage": {"input_tokens": 10, "output_tokens": 2, "total_tokens": 12},
            }
            events = [
                {"type": "response.created", "response": {**result, "status": "in_progress", "output": []}},
                {"type": "response.output_item.added", "output_index": 0, "item": item},
                {
                    "type": "response.function_call_arguments.delta",
                    "output_index": 0,
                    "item_id": "fc_one",
                    "delta": "{}",
                },
                {"type": "response.output_item.done", "output_index": 0, "item": item},
                {"type": "response.completed", "response": result},
            ]
        if not stream:
            return web.json_response(result)
        response = web.StreamResponse(headers={"Content-Type": "text/event-stream"})
        await response.prepare(request)
        data = "".join("data: " + json.dumps(event) + "\n\n" for event in events)
        if chat:
            data += "data: [DONE]\n\n"
        for start in range(0, len(data), 11):
            await response.write(data[start : start + 11].encode())
        await response.write_eof()
        return response

    async with stub_source_upstreams() as start:
        url = await start(upstream)
        created = await async_client.post(
            "/api/openrouter-accounts", json={"name": "Tool names", "apiKey": "synthetic"}
        )
        account_id = created.json()["id"]
        await async_client.patch(
            f"/api/openrouter-accounts/{account_id}", json={"selections": [{"model": "vendor/test"}]}
        )
        async with SessionLocal() as session:
            source = await session.get(ModelSource, account_id)
            source.base_url = url
            await session.commit()
        function = {"name": name, "parameters": {"type": "object", "properties": {}}}
        payload = {"model": "openrouter/vendor/test", "stream": stream}
        if chat:
            payload.update(
                messages=[{"role": "user", "content": "Use tool"}],
                tools=[{"type": "function", "function": function}],
                tool_choice={"type": "function", "function": {"name": name}},
            )
        else:
            payload.update(
                input="Use tool",
                tools=[{"type": "function", **function}],
                tool_choice={"type": "function", "name": name},
            )
        result = await async_client.post(path, json=payload)
        assert result.status_code == 200, result.text
        assert len(calls) == 1
        if stream:
            events = [parse_sse_data_json(block) for block in result.text.split("\n\n")]
            events = [event for event in events if event]
            if chat:
                returned = next(
                    event["choices"][0]["delta"]["tool_calls"][0]["function"]
                    for event in events
                    if event.get("choices")
                )
            else:
                assert next(event["item"]["name"] for event in events if "item" in event) == name
                returned = next(
                    event["response"]["output"][0] for event in events if event.get("type") == "response.completed"
                )
        else:
            data = result.json()
            returned = data["choices"][0]["message"]["tool_calls"][0]["function"] if chat else data["output"][0]
        assert returned["name"] == name
        assert returned["arguments"] == '{"text":"unchanged"}'
        async with SessionLocal() as session:
            log = await session.scalar(select(RequestLog).where(RequestLog.model_source_id == account_id))
            assert log.latency_ms is not None
            if stream:
                assert log.latency_first_token_ms is not None
                assert log.latency_ms >= log.latency_first_token_ms
            else:
                assert log.latency_first_token_ms is None
