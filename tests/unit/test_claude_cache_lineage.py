from __future__ import annotations

import logging
from datetime import UTC, datetime

import pytest
from pydantic import JsonValue

from app.modules.claude.cache_lineage import CacheLineage


class _Clock:
    def __init__(self) -> None:
        self.now_s = 1000.0

    def monotonic(self) -> float:
        return self.now_s

    def time(self) -> float:
        return self.now_s

    def now(self) -> datetime:
        return datetime.fromtimestamp(self.now_s, UTC)


_MARK: JsonValue = {"type": "ephemeral", "ttl": "1h"}
_MISS: JsonValue = {"cache_read_input_tokens": 0, "cache_creation_input_tokens": 205_653}
_HIT: JsonValue = {"cache_read_input_tokens": 201_783, "cache_creation_input_tokens": 1_433}


def _tool(name: str) -> dict[str, JsonValue]:
    return {"name": name, "description": name, "input_schema": {"type": "object"}}


def _user(text: str, *, marked: bool = False) -> dict[str, JsonValue]:
    block: dict[str, JsonValue] = {"type": "text", "text": text}
    if marked:
        block["cache_control"] = _MARK
    return {"role": "user", "content": [block]}


def _body(tools: list[str], messages: list[JsonValue]) -> dict[str, JsonValue]:
    return {
        "model": "claude-opus-5-5",
        "tools": [_tool(name) for name in tools],
        "system": [{"type": "text", "text": "identity", "cache_control": _MARK}],
        "messages": messages,
        "max_tokens": 32_000,
        "stream": True,
    }


def _misses(caplog: pytest.LogCaptureFixture) -> list[str]:
    return [record.getMessage() for record in caplog.records if "claude_cache_miss" in record.getMessage()]


def test_fork_that_drops_a_tool_names_the_parent_and_the_tool(caplog: pytest.LogCaptureFixture) -> None:
    clock = _Clock()
    lineage = CacheLineage(clock=clock)
    history: list[JsonValue] = [_user("hello"), {"role": "assistant", "content": [{"type": "text", "text": "hi"}]}]
    lineage.observe(
        conversation_id="parent",
        session_id="parent",
        source_id="claude-a",
        body=_body(["exec", "create_canvas"], history),
        usage=_HIT,
    )
    clock.now_s += 120

    with caplog.at_level(logging.INFO):
        lineage.observe(
            conversation_id="side",
            session_id="parent",
            source_id="claude-a",
            body=_body(["exec"], [*history, _user("side question")]),
            usage=_MISS,
        )

    [line] = _misses(caplog)
    assert "conversation_id=side reference=parent reference_id=parent same_source=True idle_s=120" in line
    assert "cache_write=205653 tools=removed:create_canvas system=same params=same" in line
    assert "messages=2/3 first_divergence=none" in line


def test_moved_breakpoints_and_appended_messages_are_not_a_divergence(caplog: pytest.LogCaptureFixture) -> None:
    lineage = CacheLineage(clock=_Clock())
    lineage.observe(
        conversation_id="conversation",
        session_id=None,
        source_id="claude-a",
        body=_body(["exec"], [_user("one", marked=True)]),
        usage=_HIT,
    )

    with caplog.at_level(logging.INFO):
        lineage.observe(
            conversation_id="conversation",
            session_id=None,
            source_id="claude-b",
            body=_body(
                ["exec"],
                [_user("one"), {"role": "assistant", "content": "ok"}, _user("two", marked=True)],
            ),
            usage=_MISS,
        )

    [line] = _misses(caplog)
    assert "reference=self reference_id=conversation same_source=False" in line
    assert "tools=same system=same params=same messages=1/3 first_divergence=none" in line


def test_changed_message_and_parameter_are_named(caplog: pytest.LogCaptureFixture) -> None:
    lineage = CacheLineage(clock=_Clock())
    lineage.observe(
        conversation_id="conversation",
        session_id=None,
        source_id="claude-a",
        body=_body(["exec"], [_user("one"), _user("two")]),
        usage=_HIT,
    )
    rewritten = _body(["exec"], [_user("one"), {"role": "user", "content": [{"type": "tool_result"}]}])
    rewritten["thinking"] = {"type": "adaptive"}

    with caplog.at_level(logging.INFO):
        lineage.observe(
            conversation_id="conversation", session_id=None, source_id="claude-a", body=rewritten, usage=_MISS
        )

    [line] = _misses(caplog)
    assert "params=changed(thinking)" in line
    assert "first_divergence=1 divergent_message=user[tool_result]" in line


def test_cache_hit_is_silent(caplog: pytest.LogCaptureFixture) -> None:
    lineage = CacheLineage(clock=_Clock())
    body = _body(["exec"], [_user("one")])
    lineage.observe(conversation_id="conversation", session_id=None, source_id="claude-a", body=body, usage=_HIT)

    with caplog.at_level(logging.INFO):
        lineage.observe(
            conversation_id="conversation",
            session_id=None,
            source_id="claude-a",
            body=_body(["other"], [_user("one")]),
            usage=_HIT,
        )

    assert _misses(caplog) == []


def test_miss_without_reference_is_silent_and_capacity_is_bounded(caplog: pytest.LogCaptureFixture) -> None:
    lineage = CacheLineage(capacity=1, clock=_Clock())
    lineage.observe(conversation_id="first", session_id=None, source_id="claude-a", body=_body([], []), usage=_HIT)
    lineage.observe(conversation_id="second", session_id=None, source_id="claude-a", body=_body([], []), usage=_HIT)

    with caplog.at_level(logging.INFO):
        lineage.observe(
            conversation_id="fork", session_id="first", source_id="claude-a", body=_body([], []), usage=_MISS
        )

    assert _misses(caplog) == []
