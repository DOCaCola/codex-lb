import json

import pytest

from app.core.clock import RealClock
from app.modules.model_sources.forwarding import SourceStreamUsageParser, SourceUsageHolder

pytestmark = pytest.mark.unit


class Clock(RealClock):
    current = 10.0

    def monotonic(self):
        return self.current


def feed(parser, event):
    parser.feed(("data: " + json.dumps(event, ensure_ascii=False) + "\n\n").encode())


@pytest.mark.parametrize(
    "kind",
    [
        "response.output_text.delta",
        "response.reasoning_summary_text.delta",
        "response.reasoning_text.delta",
        "response.function_call_arguments.delta",
        "response.custom_tool_call_input.delta",
    ],
)
def test_first_generated_content_and_terminal_freeze(kind):
    clock, holder = Clock(), SourceUsageHolder()
    parser = SourceStreamUsageParser(holder, response_shape="responses", clock=clock)
    clock.current = 11
    feed(parser, {"type": "response.created"})
    parser.feed(b": keepalive\n\n")
    feed(parser, {"type": "response.output_item.added", "item": {"type": "function_call", "name": "read"}})
    feed(parser, {"type": kind, "delta": ""})
    assert holder.timings.latency_first_token_ms is None
    clock.current = 12
    raw = ("data: " + json.dumps({"type": kind, "delta": "é"}, ensure_ascii=False) + "\n\n").encode()
    for byte in raw:
        parser.feed(bytes([byte]))
    assert holder.timings.latency_first_token_ms == 2000
    clock.current = 14
    feed(
        parser,
        {
            "type": "response.completed",
            "response": {
                "metrics": {"time_to_first_token_ms": 1, "generation_time_ms": 2},
                "usage": {"input_tokens": 1, "output_tokens": 100},
            },
        },
    )
    assert holder.timings.latency_ms == 4000
    clock.current = 50
    parser.end_timing()
    assert holder.timings.latency_ms == 4000
    assert holder.usage.output_tokens == 100


@pytest.mark.parametrize("terminal", ["response.completed", "response.failed", "error"])
def test_terminal_snapshot_does_not_invent_ttft(terminal):
    clock, holder = Clock(), SourceUsageHolder()
    parser = SourceStreamUsageParser(holder, response_shape="responses", clock=clock)
    clock.current = 13
    feed(parser, {"type": terminal, "response": {"output": [{"type": "message", "content": [{"text": "hello"}]}]}})
    assert holder.timings.latency_ms == 3000
    assert holder.timings.latency_first_token_ms is None


@pytest.mark.parametrize(
    "delta",
    [
        {"content": "hi"},
        {"reasoning": "think"},
        {"reasoning_content": "think"},
        {"tool_calls": [{"function": {"arguments": "{}"}}]},
    ],
)
def test_chat_ignores_role_usage_then_measures_output(delta):
    clock, holder = Clock(), SourceUsageHolder()
    parser = SourceStreamUsageParser(holder, response_shape="chat", clock=clock)
    clock.current = 11
    feed(parser, {"choices": [{"delta": {"role": "assistant"}}]})
    feed(parser, {"choices": [], "usage": {"prompt_tokens": 1, "completion_tokens": 0}})
    assert holder.timings.latency_first_token_ms is None
    clock.current = 12
    feed(parser, {"choices": [{"delta": delta}]})
    clock.current = 14
    parser.feed(b"data: [DONE]\n\n")
    assert holder.timings.latency_first_token_ms == 2000
    assert holder.timings.latency_ms == 4000


def test_unfinished_stream_retains_observed_duration_without_fabrication():
    clock, holder = Clock(), SourceUsageHolder()
    parser = SourceStreamUsageParser(holder, response_shape="responses", clock=clock)
    clock.current = 12
    parser.end_timing()
    assert holder.timings.latency_ms == 2000
    assert holder.timings.latency_first_token_ms is None
