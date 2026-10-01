from copy import deepcopy

import pytest

from app.core.openai.compaction import (
    encode_codex_lb_compaction_summary,
    lower_codex_lb_compaction_items,
    lower_opaque_compaction_items_for_model_source,
)
from app.core.openai.exceptions import ClientPayloadError
from app.core.openai.requests import ResponsesCompactRequest, ResponsesRequest
from app.core.types import JsonValue
from app.core.utils.request_id import reset_request_id, set_request_id
from app.modules.model_sources.compaction import build_source_compaction_request

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "metadata",
    [
        {},
        {"encrypted_content": None},
        {"id": "cmp_private", "internal_chat_message_metadata_passthrough": {"turn_id": "private"}},
    ],
)
def test_local_markers_preserve_summary_tools_and_native_input(metadata, caplog):
    marker = {"type": "context_compaction", **metadata}
    items: list[JsonValue] = [
        marker,
        {"role": "user", "content": "PRIVATE_SUMMARY"},
        {"type": "function_call", "call_id": "call_private", "name": "lookup", "arguments": "{}"},
        {"type": "function_call_output", "call_id": "call_private", "output": "PRIVATE_TOOL_RESULT"},
        {"role": "user", "content": [{"type": "input_image", "image_url": "data:image/png;base64,PRIVATE_IMAGE"}]},
        {"role": "user", "content": "Continue"},
    ]
    original = deepcopy(items)
    native: dict[str, JsonValue] = {"input": items}
    lower_codex_lb_compaction_items(native)
    assert native["input"] == original
    request = ResponsesRequest.model_validate({"model": "gpt-6.1-sol", "instructions": "Continue", "input": items})
    assert request.to_payload()["input"] == original
    token = set_request_id("marker-unit-request")
    try:
        source: dict[str, JsonValue] = {"input": items}
        with caplog.at_level("INFO"):
            lower_opaque_compaction_items_for_model_source(source)
    finally:
        reset_request_id(token)
    assert source["input"] == original[1:]
    assert items == original
    assert "request_id=marker-unit-request count=1" in caplog.text
    assert "PRIVATE" not in caplog.text and "cmp_private" not in caplog.text and "call_private" not in caplog.text


@pytest.mark.parametrize(
    "kind,ciphertext",
    [
        (kind, ciphertext)
        for kind in ["compaction", "compaction_summary", "context_compaction"]
        for ciphertext in [None, "OPENAI_PRIVATE_CIPHERTEXT", "", 3]
        if kind != "context_compaction" or ciphertext is not None
    ],
)
def test_only_payload_free_context_markers_are_omitted(kind, ciphertext, caplog):
    item = {"type": kind, "encrypted_content": ciphertext, "id": "cmp_private"}
    payload: dict[str, JsonValue] = {"input": [{"role": "user", "content": "PRIVATE_SUMMARY"}, item]}
    original = deepcopy(payload)
    with pytest.raises(ClientPayloadError) as error:
        lower_opaque_compaction_items_for_model_source(payload)
    assert error.value.code == "compaction_history_unavailable"
    assert error.value.param == "input[1]"
    assert payload == original
    assert f"input_index=1 item_type={kind}" in caplog.text
    assert f"ciphertext_present={ciphertext is not None}" in caplog.text
    assert "PRIVATE" not in caplog.text and "cmp_private" not in caplog.text


@pytest.mark.parametrize("field,value", [("content", "PRIVATE_CONTEXT"), ("summary", []), ("future_state", None)])
@pytest.mark.parametrize("ciphertext", [None, encode_codex_lb_compaction_summary("PRIVATE_SUMMARY")])
def test_unsupported_marker_payload_is_not_silently_discarded(field, value, ciphertext, caplog):
    payload: dict[str, JsonValue] = {
        "input": [{"type": "context_compaction", "encrypted_content": ciphertext, field: value}]
    }
    original = deepcopy(payload)
    with pytest.raises(ClientPayloadError) as error:
        lower_opaque_compaction_items_for_model_source(payload)
    assert error.value.param == "input[0]"
    assert "reason=unsupported_marker_payload" in caplog.text
    assert "PRIVATE_CONTEXT" not in caplog.text
    assert payload == original


@pytest.mark.parametrize("corrupt", [False, True])
def test_rejection_after_lowered_summary_is_atomic_and_keeps_original_index(corrupt, caplog):
    payload: dict[str, JsonValue] = {
        "input": [
            {"type": "context_compaction"},
            {"type": "compaction", "encrypted_content": encode_codex_lb_compaction_summary("PRIVATE_SUMMARY")},
            {"type": "compaction", "encrypted_content": "clb1:INVALID!" if corrupt else "OPENAI_PRIVATE_CIPHERTEXT"},
        ]
    }
    original = deepcopy(payload)
    with pytest.raises(ClientPayloadError) as error:
        lower_opaque_compaction_items_for_model_source(payload)
    assert error.value.param == "input[2]"
    assert payload == original
    assert "PRIVATE" not in caplog.text and "INVALID!" not in caplog.text
    assert "input_index=2" in caplog.text
    assert "source_compaction_markers_skipped" not in caplog.text


def test_marker_and_proxy_checkpoint_lower_together_with_one_success_diagnostic(caplog):
    payload: dict[str, JsonValue] = {
        "input": [
            {"type": "context_compaction"},
            {"type": "compaction", "encrypted_content": encode_codex_lb_compaction_summary("PORTABLE_SUMMARY")},
            {"type": "context_compaction", "encrypted_content": None},
        ]
    }
    with caplog.at_level("INFO"):
        lower_opaque_compaction_items_for_model_source(payload)
    assert "PORTABLE_SUMMARY" in str(payload)
    assert "context_compaction" not in str(payload) and "clb1:" not in str(payload)
    assert caplog.text.count("source_compaction_markers_skipped") == 1
    assert "count=2" in caplog.text and "PORTABLE_SUMMARY" not in caplog.text


def test_source_compaction_preserves_plain_summary_without_local_marker():
    compact = ResponsesCompactRequest.model_validate(
        {
            "model": "source",
            "instructions": "Summarize",
            "input": [{"type": "context_compaction"}, {"role": "user", "content": "PORTABLE_SUMMARY"}],
        }
    )
    before = compact.model_dump(mode="json")
    request = build_source_compaction_request(compact, keep_tool_declarations=False)
    assert "PORTABLE_SUMMARY" in str(request.input)
    assert "context_compaction" not in str(request.input)
    assert compact.model_dump(mode="json") == before


def test_source_compaction_rejection_indexes_before_removing_control_items():
    compact = ResponsesCompactRequest.model_validate(
        {
            "model": "source",
            "instructions": "Summarize",
            "input": [
                {"type": "additional_tools", "tools": []},
                {"type": "context_compaction"},
                {"type": "compaction", "encrypted_content": "PRIVATE_CIPHERTEXT"},
            ],
        }
    )
    before = compact.model_dump(mode="json")
    with pytest.raises(ClientPayloadError) as error:
        build_source_compaction_request(compact, keep_tool_declarations=False)
    assert error.value.param == "input[2]"
    assert compact.model_dump(mode="json") == before
