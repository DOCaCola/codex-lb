"""Identify Codex task envelopes without relaxing genuine tool-result pairing."""

from pydantic import JsonValue


def task_metadata_complete(item: dict[str, JsonValue]) -> bool:
    return all(isinstance(value := item.get(key), str) and value.strip() for key in ("id", "name", "namespace"))


def is_external_task_input(item: dict[str, JsonValue]) -> bool:
    if item.get("type") != "function_call_output" or not task_metadata_complete(item):
        return False
    call_id = item.get("call_id")
    if call_id is not None and (not isinstance(call_id, str) or call_id.strip()):
        return False
    output = item.get("output")
    if isinstance(output, str):
        return bool(output.strip())
    if not isinstance(output, list) or not output:
        return False
    meaningful = False
    for block in output:
        if not isinstance(block, dict):
            return False
        kind = block.get("type")
        if kind in ("input_text", "output_text", "text"):
            text = block.get("text")
            if not isinstance(text, str):
                return False
            meaningful |= bool(text.strip())
        elif kind == "input_image":
            url = block.get("image_url")
            if not isinstance(url, str) or not url.strip():
                return False
            if "detail" in block and block["detail"] not in ("auto", "low", "high", "original"):
                return False
            meaningful = True
        else:
            return False
    return meaningful
