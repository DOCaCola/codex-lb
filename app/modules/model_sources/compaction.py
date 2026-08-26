from __future__ import annotations

from collections.abc import Mapping

from app.core.openai.compaction import COMPACTION_PROMPT, lower_opaque_compaction_items_for_model_source
from app.core.openai.requests import ResponsesCompactRequest, ResponsesRequest
from app.core.types import JsonValue
from app.core.utils.json_guards import is_json_list, is_json_mapping

_SOURCE_COMPACTION_IMAGE_NOTE = "[image omitted for compaction]"


class SourceCompactionResultError(ValueError):
    pass


def build_source_compaction_request(payload: ResponsesCompactRequest) -> ResponsesRequest:
    compact_payload = dict(payload.to_payload())
    input_value = compact_payload.get("input")
    input_items = input_value if is_json_list(input_value) else [input_value]
    history = [
        _replace_compaction_images(item)
        for item in input_items
        if not (is_json_mapping(item) and item.get("type") == "compaction_trigger")
    ]
    source_payload: dict[str, JsonValue] = {
        "model": payload.model,
        "instructions": payload.instructions,
        "input": [
            *history,
            {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": COMPACTION_PROMPT}],
            },
        ],
        "store": False,
        "stream": False,
    }
    if payload.reasoning is not None:
        source_payload["reasoning"] = payload.reasoning.model_dump(mode="json", exclude_none=True)
    if payload.service_tier is not None:
        source_payload["service_tier"] = payload.service_tier
    lower_opaque_compaction_items_for_model_source(source_payload)
    return ResponsesRequest.model_validate(source_payload)


def extract_completed_source_compaction_summary(payload: Mapping[str, JsonValue]) -> str:
    status = payload.get("status")
    if status != "completed":
        raise SourceCompactionResultError(f"source compaction did not complete (status: {status or 'unknown'})")
    output = payload.get("output")
    if not is_json_list(output):
        raise SourceCompactionResultError("source compaction returned malformed output")
    text_parts: list[str] = []
    for item in output:
        if not is_json_mapping(item) or item.get("type") != "message":
            continue
        content = item.get("content")
        if not is_json_list(content):
            continue
        for part in content:
            if not is_json_mapping(part) or part.get("type") != "output_text":
                continue
            text = part.get("text")
            if isinstance(text, str):
                text_parts.append(text)
    summary = "".join(text_parts).strip()
    if not summary:
        raise SourceCompactionResultError("source compaction returned no summary text")
    return summary


def _replace_compaction_images(value: JsonValue) -> JsonValue:
    if is_json_list(value):
        return [_replace_compaction_images(item) for item in value]
    if not is_json_mapping(value):
        return value
    if value.get("type") == "input_image":
        return {"type": "input_text", "text": _SOURCE_COMPACTION_IMAGE_NOTE}
    return {key: _replace_compaction_images(item) for key, item in value.items()}
