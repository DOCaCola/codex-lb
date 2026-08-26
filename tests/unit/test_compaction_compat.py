from __future__ import annotations

import pytest

from app.core.openai.compaction import (
    CODEX_LB_COMPACTION_PREFIX,
    COMPACTION_SUMMARY_PREFIX,
    COMPACTION_UNAVAILABLE_NOTE,
    decode_codex_lb_compaction_summary,
    encode_codex_lb_compaction_summary,
    lower_codex_lb_compaction_items,
    lower_opaque_compaction_items_for_model_source,
)
from app.core.openai.requests import ResponsesCompactRequest, ResponsesRequest, sanitize_native_reasoning_input
from app.core.types import JsonValue
from app.modules.model_sources.compaction import (
    SourceCompactionResultError,
    build_source_compaction_request,
    extract_completed_source_compaction_summary,
)


def test_codex_lb_compaction_envelope_round_trips_and_lowers() -> None:
    envelope = encode_codex_lb_compaction_summary("finished work")
    assert envelope.startswith(CODEX_LB_COMPACTION_PREFIX)
    assert decode_codex_lb_compaction_summary(envelope) == "finished work"

    payload: dict[str, JsonValue] = {"input": [{"type": "compaction", "encrypted_content": envelope}]}
    lower_codex_lb_compaction_items(payload)

    assert payload["input"] == [
        {
            "type": "message",
            "role": "user",
            "content": [
                {
                    "type": "input_text",
                    "text": f"{COMPACTION_SUMMARY_PREFIX}\n\nfinished work",
                }
            ],
        }
    ]

    request = ResponsesRequest.model_validate(
        {
            "model": "gpt-5.6-luna",
            "instructions": "continue",
            "input": [{"type": "compaction", "encrypted_content": envelope}],
        }
    )
    assert request.to_payload()["input"] == payload["input"]


def test_malformed_proxy_envelope_becomes_explicit_unavailable_note() -> None:
    payload: dict[str, JsonValue] = {"input": [{"type": "compaction", "encrypted_content": "clb1:not-base64!"}]}
    lower_codex_lb_compaction_items(payload)
    assert COMPACTION_UNAVAILABLE_NOTE in str(payload["input"])


def test_native_opaque_compaction_is_lowered_only_for_model_sources() -> None:
    payload: dict[str, JsonValue] = {"input": [{"type": "compaction", "encrypted_content": "native-opaque"}]}
    lower_codex_lb_compaction_items(payload)
    assert payload["input"] == [{"type": "compaction", "encrypted_content": "native-opaque"}]

    lower_opaque_compaction_items_for_model_source(payload)
    assert COMPACTION_UNAVAILABLE_NOTE in str(payload["input"])


def test_native_reasoning_sanitizer_removes_foreign_output_fields() -> None:
    payload: dict[str, JsonValue] = {
        "input": [
            {
                "type": "reasoning",
                "status": "completed",
                "content": [{"type": "reasoning_text", "text": "provider thought"}],
            },
            {"type": "message", "role": "user", "content": "continue"},
        ]
    }
    sanitized = sanitize_native_reasoning_input(payload)

    assert sanitized["input"] == [
        {"type": "reasoning", "content": []},
        {"type": "message", "role": "user", "content": "continue"},
    ]
    assert "provider thought" in str(payload["input"])


def test_source_compaction_request_is_plain_tool_free_summary_turn() -> None:
    compact = ResponsesCompactRequest.model_validate(
        {
            "model": "openrouter/stealth/ox-alpha",
            "instructions": "base instructions",
            "input": [
                {"type": "compaction", "encrypted_content": "native-opaque"},
                {
                    "type": "additional_tools",
                    "role": "user",
                    "tools": [{"type": "function", "name": "desktop_tool"}],
                },
                {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_image", "image_url": "data:image/png;base64,AAAA"}],
                },
                {"type": "compaction_trigger"},
            ],
            "tools": [{"type": "function", "name": "do_work"}],
            "text": {"format": {"type": "json_schema"}},
        }
    )

    request = build_source_compaction_request(compact)
    wire = request.model_dump_for_forwarding()

    assert wire["stream"] is False
    assert wire["store"] is False
    assert "tools" not in wire
    assert "text" not in wire
    assert "compaction_trigger" not in str(wire["input"])
    assert "additional_tools" not in str(wire["input"])
    assert "desktop_tool" not in str(wire["input"])
    assert COMPACTION_UNAVAILABLE_NOTE in str(wire["input"])
    assert "[image omitted for compaction]" in str(wire["input"])
    assert "CONTEXT CHECKPOINT COMPACTION" in str(wire["input"])


def test_source_compaction_accepts_only_completed_nonempty_message_text() -> None:
    response: dict[str, JsonValue] = {
        "status": "completed",
        "output": [
            {"type": "reasoning", "content": [{"type": "reasoning_text", "text": "hidden"}]},
            {
                "type": "message",
                "content": [
                    {"type": "output_text", "text": "summary "},
                    {"type": "output_text", "text": "text"},
                ],
            },
        ],
    }
    assert extract_completed_source_compaction_summary(response) == "summary text"

    with pytest.raises(SourceCompactionResultError):
        extract_completed_source_compaction_summary({"status": "incomplete", "output": response["output"]})
    with pytest.raises(SourceCompactionResultError):
        extract_completed_source_compaction_summary({"status": "completed", "output": []})


@pytest.mark.parametrize(
    "terminal_field",
    [
        {"incomplete_details": {"reason": "max_output_tokens"}},
        {"finish_reason": "length"},
        {"stop_reason": "content_filter"},
    ],
)
def test_source_compaction_rejects_truncated_terminal_signals(
    terminal_field: dict[str, JsonValue],
) -> None:
    response: dict[str, JsonValue] = {
        "status": "completed",
        "output": [
            {
                "type": "message",
                "status": "completed",
                "content": [{"type": "output_text", "text": "partial summary"}],
            }
        ],
        **terminal_field,
    }

    with pytest.raises(SourceCompactionResultError, match="incomplete|truncated"):
        extract_completed_source_compaction_summary(response)


def test_source_compaction_rejects_incomplete_message_item() -> None:
    response: dict[str, JsonValue] = {
        "status": "completed",
        "output": [
            {
                "type": "message",
                "status": "incomplete",
                "content": [{"type": "output_text", "text": "partial summary"}],
            }
        ],
    }

    with pytest.raises(SourceCompactionResultError, match="message did not complete"):
        extract_completed_source_compaction_summary(response)
