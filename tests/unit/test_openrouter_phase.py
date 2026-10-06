import json

import pytest

from app.core.utils.sse import parse_sse_data_json
from app.modules.openrouter.phase import assign_phases, project_phases

pytestmark = pytest.mark.unit


def _message(item_id: str, **extra: object) -> dict[str, object]:
    return {
        "type": "message",
        "id": item_id,
        "role": "assistant",
        "content": [{"type": "output_text", "text": item_id}],
        **extra,
    }


def _call(item_id: str) -> dict[str, object]:
    return {"type": "function_call", "id": item_id, "call_id": item_id, "name": "shell", "arguments": "{}"}


def _reasoning(item_id: str) -> dict[str, object]:
    return {"type": "reasoning", "id": item_id, "summary": []}


def _event(payload: dict[str, object]) -> bytes:
    return f"event: {payload['type']}\ndata: {json.dumps(payload)}\n\n".encode()


def _turn(items: list[dict[str, object]], terminal: str, status: str) -> list[bytes]:
    frames = [_event({"type": "response.created", "response": {"status": "in_progress", "output": []}})]
    for index, item in enumerate(items):
        frames.append(_event({"type": "response.output_item.added", "output_index": index, "item": item}))
        frames.append(_event({"type": "response.output_item.done", "output_index": index, "item": item}))
    frames.append(_event({"type": terminal, "response": {"status": status, "output": items}}))
    return frames


async def _project(frames: list[bytes], *, error: Exception | None = None) -> list[str]:
    async def body():
        for frame in frames:
            yield frame
        if error is not None:
            raise error

    return [chunk.decode() async for chunk in project_phases(body())]


def _done_phases(blocks: list[str]) -> dict[str, object]:
    phases: dict[str, object] = {}
    for block in blocks:
        payload = parse_sse_data_json(block)
        assert payload is not None
        if payload["type"] == "response.output_item.done":
            item = payload["item"]
            phases[item["id"]] = item.get("phase")
    return phases


def _terminal_phases(blocks: list[str]) -> dict[str, object]:
    payload = parse_sse_data_json(blocks[-1])
    assert payload is not None
    return {item["id"]: item.get("phase") for item in payload["response"]["output"]}


@pytest.mark.asyncio
async def test_last_message_of_a_finished_turn_is_final_and_earlier_messages_are_commentary():
    blocks = await _project(
        _turn(
            [_message("plan"), _reasoning("think"), _message("note"), _message("answer")],
            "response.completed",
            "completed",
        )
    )

    expected = {"plan": "commentary", "think": None, "note": "commentary", "answer": "final_answer"}
    assert _done_phases(blocks) == expected
    assert _terminal_phases(blocks) == expected
    assert all(block.startswith("event: ") for block in blocks)
    order = [parse_sse_data_json(block)["type"] for block in blocks]
    assert order[:4] == [
        "response.created",
        "response.output_item.added",
        "response.output_item.done",
        "response.output_item.added",
    ]


@pytest.mark.asyncio
async def test_message_closing_a_tool_requesting_turn_is_commentary():
    blocks = await _project(_turn([_call("call"), _message("waiting")], "response.completed", "completed"))

    assert _done_phases(blocks)["waiting"] == "commentary"
    assert _terminal_phases(blocks)["waiting"] == "commentary"


@pytest.mark.parametrize(("terminal", "status"), [("response.incomplete", "incomplete"), ("response.failed", "failed")])
@pytest.mark.asyncio
async def test_truncated_turn_leaves_its_last_message_unphased(terminal, status):
    blocks = await _project(_turn([_message("plan"), _message("partial")], terminal, status))

    assert _done_phases(blocks) == {"plan": "commentary", "partial": None}
    assert _terminal_phases(blocks) == {"plan": "commentary", "partial": None}


@pytest.mark.asyncio
async def test_upstream_phase_stands_and_unchanged_frames_pass_verbatim():
    frames = _turn([_message("answer", phase="commentary")], "response.completed", "completed")

    assert [block.encode() for block in await _project(frames)] == frames


@pytest.mark.asyncio
async def test_stream_failure_releases_the_finished_message_before_raising():
    frames = _turn([_message("answer")], "response.completed", "completed")[:-1]
    blocks: list[str] = []

    with pytest.raises(RuntimeError):
        async for chunk in project_phases(_failing(frames)):
            blocks.append(chunk.decode())

    assert _done_phases(blocks) == {"answer": None}


async def _failing(frames: list[bytes]):
    for frame in frames:
        yield frame
    raise RuntimeError("source disconnected")


def test_whole_response_gets_the_same_phases():
    response = {"status": "completed", "output": [_message("plan"), _reasoning("think"), _message("answer")]}
    assign_phases(response)
    assert [item.get("phase") for item in response["output"]] == ["commentary", None, "final_answer"]

    incomplete = {"status": "incomplete", "output": [_message("partial")]}
    assign_phases(incomplete)
    assert "phase" not in incomplete["output"][0]

    native = {"status": "completed", "output": [_message("answer", phase="commentary")]}
    assign_phases(native)
    assert native["output"][0]["phase"] == "commentary"
