"""Generated-content detection for gateway-observed OpenRouter timing."""

from collections.abc import Mapping

from app.core.types import JsonValue

_GENERATED_DELTAS = frozenset(
    {
        "response.output_text.delta",
        "response.refusal.delta",
        "response.reasoning.delta",
        "response.reasoning_text.delta",
        "response.reasoning_summary_text.delta",
        "response.function_call_arguments.delta",
        "response.custom_tool_call_input.delta",
    }
)


def has_generated_content(event: Mapping[str, JsonValue], *, responses: bool) -> bool:
    if responses:
        kind = event.get("type")
        if isinstance(kind, str) and kind in _GENERATED_DELTAS:
            return isinstance(event.get("delta"), str) and bool(event["delta"])
        return False
    choices = event.get("choices")
    if not isinstance(choices, list):
        return False
    for choice in choices:
        delta = choice.get("delta") if isinstance(choice, dict) else None
        if not isinstance(delta, dict):
            continue
        if any(
            isinstance(delta.get(key), str) and delta[key]
            for key in ("content", "reasoning", "reasoning_content", "refusal")
        ):
            return True
        calls = delta.get("tool_calls")
        if isinstance(calls, list):
            for call in calls:
                function = call.get("function") if isinstance(call, dict) else None
                if isinstance(function, dict) and isinstance(function.get("arguments"), str) and function["arguments"]:
                    return True
    return False
