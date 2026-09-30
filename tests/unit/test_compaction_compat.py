from __future__ import annotations

import json

import pytest

from app.core.openai.compaction import (
    CODEX_LB_COMPACTION_PREFIX,
    COMPACTION_SUMMARY_PREFIX,
    decode_codex_lb_compaction_summary,
    encode_codex_lb_compaction_summary,
    lower_codex_lb_compaction_items,
    lower_opaque_compaction_items_for_model_source,
)
from app.core.openai.exceptions import ClientPayloadError
from app.core.openai.requests import (
    ResponsesCompactRequest,
    ResponsesRequest,
    sanitize_native_reasoning_input,
    strip_unstored_lookup_item_ids,
)
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


def test_malformed_proxy_envelope_rejects_history_loss() -> None:
    payload: dict[str, JsonValue] = {"input": [{"type": "compaction", "encrypted_content": "clb1:not-base64!"}]}
    with pytest.raises(ClientPayloadError, match="corrupt"):
        lower_codex_lb_compaction_items(payload)


def test_native_opaque_compaction_is_lowered_only_for_model_sources() -> None:
    payload: dict[str, JsonValue] = {"input": [{"type": "compaction", "encrypted_content": "native-opaque"}]}
    lower_codex_lb_compaction_items(payload)
    assert payload["input"] == [{"type": "compaction", "encrypted_content": "native-opaque"}]

    with pytest.raises(ClientPayloadError, match="original provider"):
        lower_opaque_compaction_items_for_model_source(payload)


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
        {"type": "reasoning", "summary": [{"type": "summary_text", "text": "provider thought"}], "content": []},
        {"type": "message", "role": "user", "content": "continue"},
    ]
    assert "provider thought" in str(payload["input"])


def test_unstored_responses_sanitizer_removes_lookup_ids_only() -> None:
    input_items: list[JsonValue] = [
        {"type": "message", "id": "msg_tmp_1", "role": "assistant", "content": "hello"},
        {
            "type": "function_call",
            "id": "fc_tmp_1",
            "call_id": "call_1",
            "name": "ping",
            "arguments": "{}",
        },
        {"type": "reasoning", "id": "rs_tmp_jp91555aji", "content": []},
        {"type": "item_reference", "id": "msg_stored"},
        {"type": "compaction", "id": "cmp_bound", "encrypted_content": "opaque"},
    ]
    unstored: dict[str, JsonValue] = {"store": False, "input": input_items}

    sanitized = strip_unstored_lookup_item_ids(unstored)

    assert sanitized["input"] == [
        {"type": "message", "role": "assistant", "content": "hello"},
        {"type": "function_call", "call_id": "call_1", "name": "ping", "arguments": "{}"},
        {"type": "reasoning", "content": []},
        {"type": "item_reference", "id": "msg_stored"},
        {"type": "compaction", "id": "cmp_bound", "encrypted_content": "opaque"},
    ]
    assert unstored["input"] == input_items
    assert strip_unstored_lookup_item_ids({"store": True, "input": input_items})["input"] == input_items
    assert strip_unstored_lookup_item_ids({"input": input_items})["input"] == input_items


def test_source_compaction_request_is_plain_tool_free_summary_turn() -> None:
    compact = ResponsesCompactRequest.model_validate(
        {
            "model": "openrouter/stealth/ox-alpha",
            "instructions": "base instructions",
            "input": [
                {"type": "compaction", "encrypted_content": encode_codex_lb_compaction_summary("retained history")},
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
    assert "retained history" in str(wire["input"])
    assert isinstance(compact.input, list) and isinstance(wire["input"], list)
    assert compact.input[2] in wire["input"]
    assert wire["truncation"] == "disabled"
    assert "CONTEXT CHECKPOINT COMPACTION" in str(wire["input"])


def test_source_compaction_preserves_history_above_native_wire_budget() -> None:
    items = [
        {"role": "user", "content": "EARLIEST: preserve this decision"},
        {"type": "function_call", "name": "inspect", "namespace": "functions", "call_id": "call_1", "arguments": "{}"},
        {"type": "function_call_output", "call_id": "call_1", "output": "MIDDLE: " + "x" * 600_000},
        {"role": "assistant", "content": "tool work completed"},
        {"role": "user", "content": "LATEST: resume this task"},
        {"type": "compaction_trigger"},
    ]
    compact = ResponsesCompactRequest.model_validate({"model": "source", "instructions": "summarize", "input": items})
    original = compact.model_dump(mode="json")
    request = build_source_compaction_request(compact)
    assert isinstance(compact.input, list) and isinstance(request.input, list)
    assert request.input[:-1] == compact.input[:-1]
    assert compact.model_dump(mode="json") == original


def test_source_compaction_overrides_cannot_replace_history_or_enable_truncation_tools() -> None:
    from app.db.models import ModelSource, ModelSourceModel
    from app.modules.proxy.api import _shape_source_responses_payload

    compact = ResponsesCompactRequest.model_validate(
        {"model": "source", "instructions": "summarize", "input": "all original history"}
    )
    request = build_source_compaction_request(compact)
    source = ModelSource(
        id="compact-source",
        name="Compact",
        kind="openai_compatible",
        supports_responses=True,
        models=[
            ModelSourceModel(
                model="source",
                is_enabled=True,
                raw_metadata_json=json.dumps(
                    {
                        "source_request_overrides": {
                            "input": [],
                            "instructions": "different task",
                            "tools": [{"type": "function", "name": "execute"}],
                            "truncation": "auto",
                            "text": {"format": {"type": "json_object"}},
                            "previous_response_id": "missing",
                            "store": True,
                            "reasoning": {"effort": "high"},
                        }
                    }
                ),
            )
        ],
    )
    wire = _shape_source_responses_payload(request, source, api_key=None, require_complete_history=True)
    assert wire["input"] == request.input
    assert wire["instructions"] == "summarize"
    assert wire["truncation"] == "disabled"
    assert wire["store"] is False
    assert "tools" not in wire and "text" not in wire and "previous_response_id" not in wire
    assert wire["reasoning"] == {"effort": "high"}


@pytest.mark.parametrize("handle", ["previous_response_id", "conversation"])
def test_source_compaction_requires_materialized_history(handle: str) -> None:
    compact = ResponsesCompactRequest.model_validate(
        {"model": "source", "instructions": "summarize", "input": [], handle: "stored_history"}
    )
    with pytest.raises(ClientPayloadError) as error:
        build_source_compaction_request(compact)
    assert error.value.code == "compaction_history_unavailable"
    assert error.value.param == handle


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
