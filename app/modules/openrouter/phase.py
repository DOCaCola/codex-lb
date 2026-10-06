"""The Responses phase of OpenRouter assistant messages.

OpenRouter relays ``phase`` only from models that emit it natively (OpenAI's
GPT-5.3 Codex through GPT-5.5); every other model's assistant messages arrive
without one. Codex seeds forked and subagent histories with final-answer
messages only, so a phase-less answer is lost there. A message followed by
more output is commentary; the last message of a completed turn that requests
no tool call is the final answer; a truncated or failed turn leaves it unknown.
A phase sent by the upstream always stands.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import aclosing

from app.core.types import JsonValue
from app.core.utils.sse import parse_sse_data_json
from app.modules.openrouter.tool_names import replace_sse_data, sse_frames

# Client-executed calls: a turn that requests one continues after the client runs it.
_EXECUTABLE_ITEMS = frozenset({"function_call", "custom_tool_call"})
_TERMINAL_EVENTS = frozenset({"response.completed", "response.incomplete", "response.failed"})


def assign_phases(response: dict[str, JsonValue]) -> None:
    """Give the phase-less assistant messages of a whole Responses object their phase."""
    output = response.get("output")
    if not isinstance(output, list):
        return
    requests_call = any(isinstance(item, dict) and item.get("type") in _EXECUTABLE_ITEMS for item in output)
    _assign(output, _closing_phase(completed=response.get("status") == "completed", requests_call=requests_call))


async def project_phases(body: AsyncGenerator[bytes, None]) -> AsyncGenerator[bytes, None]:
    """Responses SSE with each phase-less assistant message's ``output_item.done`` carrying its phase.

    The done event is held until the next output item or the terminal decides
    the phase; its text has already streamed, so holding it adds no latency.
    """
    held: tuple[str, dict[str, JsonValue]] | None = None
    requests_call = False
    async with aclosing(body), aclosing(sse_frames(body)) as events:
        try:
            async for event in events:
                payload = parse_sse_data_json(event)
                kind = payload.get("type") if payload is not None else None
                if payload is None:
                    yield event.encode()
                elif kind == "response.output_item.done" and _unphased_message(payload.get("item")):
                    held = (event, payload)
                elif kind == "response.output_item.added":
                    if held is not None:
                        yield _released(held, "commentary")
                        held = None
                    item = payload.get("item")
                    requests_call = requests_call or (isinstance(item, dict) and item.get("type") in _EXECUTABLE_ITEMS)
                    yield event.encode()
                elif kind in _TERMINAL_EVENTS:
                    closing = _closing_phase(completed=kind == "response.completed", requests_call=requests_call)
                    if held is not None:
                        yield _released(held, closing)
                        held = None
                    response = payload.get("response")
                    output = response.get("output") if isinstance(response, dict) else None
                    if isinstance(output, list) and _assign(output, closing):
                        yield replace_sse_data(event, payload)
                    else:
                        yield event.encode()
                else:
                    yield event.encode()
        except Exception:
            # A stream ending without a terminal still delivers its finished message, phase unknown.
            if held is not None:
                yield held[0].encode()
            raise
        if held is not None:
            yield held[0].encode()


def _closing_phase(*, completed: bool, requests_call: bool) -> str | None:
    if not completed:
        return None
    return "commentary" if requests_call else "final_answer"


def _unphased_message(item: JsonValue) -> bool:
    return (
        isinstance(item, dict)
        and item.get("type") == "message"
        and item.get("role") == "assistant"
        and item.get("phase") is None
    )


def _assign(output: list[JsonValue], closing: str | None) -> bool:
    changed = False
    for index, item in enumerate(output):
        if not _unphased_message(item):
            continue
        phase = "commentary" if index < len(output) - 1 else closing
        if phase is not None:
            assert isinstance(item, dict)
            item["phase"] = phase
            changed = True
    return changed


def _released(held: tuple[str, dict[str, JsonValue]], phase: str | None) -> bytes:
    event, payload = held
    if phase is None:
        return event.encode()
    item = payload["item"]
    assert isinstance(item, dict)
    item["phase"] = phase
    return replace_sse_data(event, payload)
