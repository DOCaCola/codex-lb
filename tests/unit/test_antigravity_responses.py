from __future__ import annotations

import json
from typing import Any, cast

import pytest
from cryptography.fernet import Fernet

from app.core.crypto import TokenEncryptor
from app.modules.antigravity.errors import AntigravityError
from app.modules.antigravity.opaque import AntigravityOpaqueState, ThoughtScope
from app.modules.antigravity.responses import EmptyCompletion, GeminiProjection, Usage
from app.modules.antigravity.tool_names import GoogleToolNames
from app.modules.claude.tool_names import ToolIdentity

OPAQUE = AntigravityOpaqueState(TokenEncryptor(key=Fernet.generate_key()))
SCOPE = ThoughtScope("src-1", "project-1", "gemini-3.8-flash", False, "client-1")


def _projection(show_summary: bool = True) -> GeminiProjection:
    tools = GoogleToolNames()
    tools.add(ToolIdentity("shell", None, False))
    return GeminiProjection("antigravity/gemini-3.8-flash", SCOPE, tools, OPAQUE, show_summary)


def _line(*parts: dict[str, Any], finish: str | None = None, usage: dict[str, int] | None = None) -> dict[str, Any]:
    candidate: dict[str, Any] = {"content": {"role": "model", "parts": list(parts)}}
    if finish:
        candidate["finishReason"] = finish
    response: dict[str, Any] = {"candidates": [candidate], "responseId": "abc"}
    if usage:
        response["usageMetadata"] = usage
    return {"response": response, "traceId": "t"}


def _run(projection: GeminiProjection, *lines: dict[str, Any]) -> list[dict[str, Any]]:
    return [event for line in lines for event in projection.consume(line)]  # type: ignore[arg-type]


def test_thought_and_answer_become_reasoning_and_final_message() -> None:
    projection = _projection()
    events = _run(
        projection,
        _line({"text": "think", "thought": True}),
        _line({"text": "Hello", "thoughtSignature": "sig-1"}),
        _line(
            {"text": " world"},
            finish="STOP",
            usage={
                "promptTokenCount": 10,
                "cachedContentTokenCount": 4,
                "candidatesTokenCount": 3,
                "thoughtsTokenCount": 2,
            },
        ),
    )
    kinds = [event["type"] for event in events]
    assert kinds[:2] == ["response.created", "response.in_progress"]
    assert "response.reasoning_summary_text.delta" in kinds
    final = events[-1]
    assert final["type"] == "response.completed"
    response = final["response"]
    assert response["id"] == "resp_abc"
    reasoning, message = response["output"]
    assert reasoning["summary"] == [{"type": "summary_text", "text": "think"}]
    assert message["phase"] == "final_answer"
    assert message["content"][0]["text"] == "Hello world"
    assert response["usage"] == {
        "input_tokens": 10,
        "input_tokens_details": {"cached_tokens": 4},
        "output_tokens": 5,
        "output_tokens_details": {"reasoning_tokens": 2},
        "total_tokens": 15,
    }
    sealed = OPAQUE.open(reasoning["encrypted_content"], client_scope="client-1", param="input")
    # The step's signature arrives on the first part after the thoughts and seals with them.
    assert (sealed.text, sealed.signature) == ("think", "sig-1")


def test_signature_on_a_call_is_sealed_ahead_of_the_call() -> None:
    projection = _projection()
    events = _run(
        projection,
        _line({"text": "Checking.", "thought": False}),
        _line(
            {"functionCall": {"id": "fc-1", "name": "shell", "args": {"command": "ls"}}, "thoughtSignature": "sig-9"}
        ),
        _line(finish="STOP"),
    )
    output = events[-1]["response"]["output"]
    assert [item["type"] for item in output] == ["message", "reasoning", "function_call"]
    assert output[0]["phase"] == "commentary"
    assert OPAQUE.open(output[1]["encrypted_content"], client_scope="client-1", param="input").signature == "sig-9"
    call = output[2]
    assert (call["call_id"], call["name"], json.loads(call["arguments"])) == ("fc-1", "shell", {"command": "ls"})


def test_hidden_summary_still_seals_reasoning() -> None:
    projection = _projection(show_summary=False)
    events = _run(projection, _line({"text": "secret", "thought": True}), _line({"text": "ok"}, finish="STOP"))
    assert all(not event["type"].startswith("response.reasoning_summary") for event in events)
    reasoning = events[-1]["response"]["output"][0]
    assert reasoning["summary"] == []
    assert OPAQUE.open(reasoning["encrypted_content"], client_scope="client-1", param="input").text == "secret"


def test_reasoning_only_completion_is_empty() -> None:
    projection = _projection()
    with pytest.raises(EmptyCompletion):
        _run(projection, _line({"text": "hmm", "thought": True}, finish="STOP"))


def test_retry_usage_carries_the_earlier_attempt() -> None:
    projection = _projection()
    projection.prior = Usage(prompt=100, cached=0, candidates=0, thoughts=7)
    events = _run(
        projection, _line({"text": "ok"}, finish="STOP", usage={"promptTokenCount": 100, "candidatesTokenCount": 1})
    )
    usage = events[-1]["response"]["usage"]
    assert (usage["input_tokens"], usage["output_tokens"]) == (200, 8)


@pytest.mark.parametrize(("finish", "reason"), [("MAX_TOKENS", "max_output_tokens"), ("SAFETY", "content_filter")])
def test_incomplete_finishes(finish: str, reason: str) -> None:
    events = _run(_projection(), _line({"text": "partial"}, finish=finish))
    assert events[-1]["type"] == "response.incomplete"
    assert events[-1]["response"]["incomplete_details"] == {"reason": reason}


def test_prompt_block_is_a_content_filter() -> None:
    events = _run(_projection(), {"response": {"promptFeedback": {"blockReason": "SAFETY"}}})
    assert events[-1]["response"]["incomplete_details"] == {"reason": "content_filter"}


@pytest.mark.parametrize(
    "line",
    [
        _line({"functionCall": {"name": "rm_rf", "args": {}}}),
        _line(finish="MALFORMED_FUNCTION_CALL"),
        _line({"inlineData": {"mimeType": "image/png", "data": ""}}),
        {"traceId": "t"},
    ],
)
def test_invalid_upstream_streams_fail(line: dict[str, Any]) -> None:
    with pytest.raises(AntigravityError) as raised:
        _run(_projection(), line)
    assert raised.value.code == "invalid_upstream_response"


def test_data_after_finish_is_rejected() -> None:
    projection = _projection()
    _run(projection, _line({"text": "done"}, finish="STOP"))
    with pytest.raises(AntigravityError):
        _run(projection, _line({"text": "more"}))


def test_interrupt_closes_the_open_message_without_phase() -> None:
    projection = _projection()
    _run(projection, _line({"text": "partial"}))
    [*_, done] = projection.interrupt()
    assert done["type"] == "response.output_item.done"
    assert "phase" not in cast(dict[str, Any], done["item"])
