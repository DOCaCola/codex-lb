from __future__ import annotations

from typing import Any, cast

import pytest

from app.core.openai.encrypted_content import (
    ENCRYPTED_FUNCTION_OUTPUT_REJECTION,
    MAX_DIGESTS,
    OMITTED_ENCRYPTED_PART_TEXT,
    REJECTED_COMPACTION_NOTE,
    REJECTED_ENCRYPTED_CONTENT,
    RejectedEncryptedContent,
    is_encrypted_content_rejection,
    remember_rejected_encrypted_content,
    remember_rejected_encrypted_content_text,
    strip_rejected_encrypted_content,
    strip_rejected_encrypted_content_text,
)
from app.core.openai.requests import sanitize_native_responses_input
from app.core.types import JsonValue
from app.core.usage.request_operation import RequestOperation, reset_request_operation, set_request_operation

RESPONSES = RequestOperation.RESPONSES
HANDOFF = RequestOperation.CHECKPOINT_HANDOFF


def _reasoning(ciphertext: str) -> dict[str, JsonValue]:
    return {"type": "reasoning", "summary": [], "encrypted_content": ciphertext}


def _tool_output(ciphertext: str) -> dict[str, JsonValue]:
    return {
        "type": "function_call_output",
        "call_id": "call_1",
        "output": [
            {"type": "input_text", "text": "visible"},
            {"type": "encrypted_content", "encrypted_content": ciphertext},
        ],
    }


USER: dict[str, JsonValue] = {"role": "user", "content": [{"type": "input_text", "text": "hello"}]}


class _Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


@pytest.mark.parametrize(
    ("code", "message", "expected"),
    [
        ("invalid_encrypted_content", "anything", True),
        ("invalid_request_error", ENCRYPTED_FUNCTION_OUTPUT_REJECTION, True),
        (
            None,
            "The encrypted content for item rs_1 could not be verified. "
            "Reason: Encrypted content item_id did not match the target item id.",
            True,
        ),
        (None, "The encrypted_content of this reasoning item was not issued to this caller.", True),
        ("server_error", "An error occurred while processing your request.", False),
        (None, "The encrypted content for item rs_1 is missing.", False),
        (None, None, False),
    ],
)
def test_only_explicit_upstream_identities_qualify(code, message, expected):
    assert is_encrypted_content_rejection(code, message) is expected


def test_strip_removes_only_remembered_ciphertext_of_each_carrier():
    store = RejectedEncryptedContent()
    compaction = {"type": "compaction", "encrypted_content": "compaction-refused"}
    assert store.remember([_reasoning("reasoning-refused"), _tool_output("output-refused"), compaction]) == 3

    result = store.strip(
        [
            USER,
            _reasoning("reasoning-refused"),
            _reasoning("reasoning-fresh"),
            _tool_output("output-refused"),
            compaction,
        ]
    )

    assert result is not None
    stripped, count = result
    assert count == 3
    assert stripped == [
        USER,
        _reasoning("reasoning-fresh"),
        {
            "type": "function_call_output",
            "call_id": "call_1",
            "output": [
                {"type": "input_text", "text": "visible"},
                {"type": "input_text", "text": OMITTED_ENCRYPTED_PART_TEXT},
            ],
        },
        {"type": "message", "role": "user", "content": [{"type": "input_text", "text": REJECTED_COMPACTION_NOTE}]},
    ]


def test_remember_counts_only_new_digests_and_strip_ignores_unrelated_input():
    store = RejectedEncryptedContent()
    assert store.remember([_reasoning("a")]) == 1
    assert store.remember([_reasoning("a")]) == 0
    assert store.remember([USER]) == 0
    assert store.strip([USER, _reasoning("b")]) is None


def test_entries_expire_unless_hit_and_hits_refresh_retention():
    clock = _Clock()
    store = RejectedEncryptedContent(retention_seconds=100, clock=clock)
    store.remember([_reasoning("kept"), _reasoning("expired")])

    clock.now += 60
    assert store.strip([_reasoning("kept")]) is not None
    clock.now += 60
    assert store.strip([_reasoning("expired")]) is None
    assert store.strip([_reasoning("kept")]) is not None
    # An expired digest counts as new again.
    assert store.remember([_reasoning("expired")]) == 1


def test_store_evicts_least_recently_used_digest_beyond_capacity():
    store = RejectedEncryptedContent(max_digests=2)
    store.remember([_reasoning("first")])
    store.remember([_reasoning("second")])
    assert store.strip([_reasoning("first")]) is not None
    store.remember([_reasoning("third")])

    assert store.strip([_reasoning("second")]) is None
    assert store.strip([_reasoning("first")]) is not None
    assert store.strip([_reasoning("third")]) is not None
    assert MAX_DIGESTS == 20_000


def test_checkpoint_handoff_neither_remembers_nor_strips():
    assert remember_rejected_encrypted_content([_reasoning("handoff")], HANDOFF) == 0
    remember_rejected_encrypted_content([_reasoning("refused")], RESPONSES)
    payload: dict[str, JsonValue] = {"input": [_reasoning("refused")]}

    assert strip_rejected_encrypted_content(payload, HANDOFF) is payload
    assert strip_rejected_encrypted_content(payload, RESPONSES) == {"input": []}


def test_text_helpers_round_trip_serialized_bodies():
    body = '{"type":"response.create","input":[{"type":"reasoning","summary":[],"encrypted_content":"refused"}]}'
    assert strip_rejected_encrypted_content_text(body, RESPONSES) is None
    assert remember_rejected_encrypted_content_text(body, RESPONSES) == 1
    assert strip_rejected_encrypted_content_text(body, RESPONSES) == '{"type":"response.create","input":[]}'
    assert strip_rejected_encrypted_content_text(None, RESPONSES) is None


def test_native_sanitizer_strips_ciphertext_refused_earlier():
    REJECTED_ENCRYPTED_CONTENT.remember([_tool_output("refused")])
    token = set_request_operation(RESPONSES)
    try:
        sanitized = sanitize_native_responses_input(
            {
                "model": "gpt-5.4",
                "input": [
                    USER,
                    {"type": "function_call", "call_id": "call_1", "name": "shell", "arguments": "{}"},
                    _tool_output("refused"),
                ],
            }
        )
    finally:
        reset_request_operation(token)

    output_item = cast(list[dict[str, Any]], sanitized["input"])[-1]
    assert output_item["type"] == "function_call_output"
    assert {"type": "input_text", "text": OMITTED_ENCRYPTED_PART_TEXT} in output_item["output"]
    assert "refused" not in str(sanitized)
