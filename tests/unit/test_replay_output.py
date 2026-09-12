import pytest

from app.core.types import JsonValue
from app.modules.proxy.replay_output import ReplayOutputCollector


def test_completed_items_are_ordered_and_replaced_not_duplicated():
    collector = ReplayOutputCollector()
    collector.retain({"output_index": 1, "item": {"type": "message", "id": "old"}})
    collector.retain({"output_index": 0, "item": {"type": "reasoning"}})
    collector.retain({"output_index": 1, "item": {"type": "message", "id": "new"}})
    assert collector.finish([]) == [{"type": "reasoning"}, {"type": "message", "id": "new"}]
    assert collector.finish([]) == []


@pytest.mark.parametrize("terminal", [[], None, "malformed", {}])
def test_non_array_or_empty_terminal_reconstructs(terminal):
    collector = ReplayOutputCollector()
    item = {"type": "custom_tool_call", "call_id": "call_1", "input": "{}"}
    collector.retain({"output_index": 0, "item": item})
    assert collector.finish(terminal) == [item]


@pytest.mark.parametrize("limits", [{"max_items": 1}, {"max_bytes": 40}])
def test_overflow_never_retains_partial_output(limits):
    collector = ReplayOutputCollector(**limits)
    collector.retain({"output_index": 0, "item": {"type": "message"}})
    collector.retain({"output_index": 1, "item": {"type": "custom_tool_call"}})
    assert collector.finish([]) is None
    collector.retain({"output_index": 0, "item": {"type": "message"}})
    assert collector.finish([]) == [{"type": "message"}]


@pytest.mark.parametrize("index", [None, -1, True, "0"])
def test_unidentifiable_item_prevents_partial_replay(index):
    collector = ReplayOutputCollector()
    collector.retain({"output_index": index, "item": {"type": "message"}})
    assert collector.finish([]) is None


def test_authoritative_terminal_wins_even_after_overflow():
    collector = ReplayOutputCollector(max_items=0)
    collector.retain({"output_index": 0, "item": {"type": "message"}})
    terminal: list[JsonValue] = [{"type": "custom_tool_call", "call_id": "complete"}]
    assert collector.finish(terminal) == terminal
    assert collector.finish([]) == []


def test_abandoned_attempt_is_discarded():
    collector = ReplayOutputCollector()
    collector.retain({"output_index": 0, "item": {"type": "custom_tool_call", "call_id": "abandoned"}})
    collector.clear()
    assert collector.finish([]) == []
