from __future__ import annotations

import uuid
from typing import Any, cast

from app.modules.antigravity.inference import cascade_id, envelope
from app.modules.antigravity.schemas import CatalogFamily

GEMINI = CatalogFamily(
    id="gemini-3.8-flash",
    display_name="Gemini 3.8 Flash",
    tiers={"low": "gemini-3.8-flash-low", "high": "gemini-3.8-flash-high"},
    model_enums={"gemini-3.8-flash-high": "MODEL_PLACEHOLDER_M900"},
    api_provider="API_PROVIDER_GOOGLE_GEMINI",
    quota_family="gemini",
)
CLAUDE = CatalogFamily(
    id="claude-opus-5-5-thinking",
    display_name="Claude Opus 5.5 (Thinking)",
    model_enums={"claude-opus-5-5-thinking": "MODEL_PLACEHOLDER_M905"},
    api_provider="API_PROVIDER_ANTHROPIC_VERTEX",
    quota_family="claude",
)
CASCADE = cascade_id("key-1", "conversation-1")
USER: dict[str, Any] = {"role": "user", "parts": [{"text": "list files"}]}
CALL: dict[str, Any] = {
    "role": "model",
    "parts": [
        {"text": "plan", "thought": True},
        {"functionCall": {"name": "shell", "args": {"command": "ls"}}, "thoughtSignature": "sig"},
    ],
}
# The CLI sends tool results with role "model" (agy 1.4.10 tool capture).
RESULT: dict[str, Any] = {
    "role": "model",
    "parts": [{"functionResponse": {"name": "shell", "response": {"output": "a"}}}],
}
ANSWER: dict[str, Any] = {"role": "model", "parts": [{"text": "done"}]}


def _request(*contents: dict[str, Any]) -> dict[str, Any]:
    return {
        "contents": list(contents),
        "systemInstruction": {"role": "user", "parts": [{"text": "system"}]},
        "tools": [{"functionDeclarations": []}],
        "generationConfig": {"maxOutputTokens": 65536},
    }


def _envelope(request: dict[str, Any], family: CatalogFamily = GEMINI) -> dict[str, Any]:
    wire = next(iter(family.model_enums))
    body = envelope(
        request,
        family=family,
        wire=wire,
        project_id="project-1",
        session_id="-3750763034362895579",
        cascade=CASCADE,
    )
    return cast(dict[str, Any], body)


def test_tool_continuation_matches_the_captured_native_envelope() -> None:
    body = _envelope(_request(USER, CALL, RESULT))
    inner = body["request"]
    labels = inner["labels"]

    assert list(body) == ["project", "requestId", "request", "model", "userAgent", "requestType"]
    assert list(inner) == ["contents", "systemInstruction", "tools", "labels", "generationConfig", "sessionId"]
    assert list(labels) == [
        "cascade_id",
        "last_step_index",
        "model_enum",
        "request_id",
        "root_cascade_id",
        "trajectory_id",
        "used_non_gemini_model",
    ]
    trajectory = labels["trajectory_id"]
    assert labels == {
        "cascade_id": CASCADE,
        "last_step_index": "2",
        "model_enum": "MODEL_PLACEHOLDER_M900",
        "request_id": f"{trajectory}-1",
        "root_cascade_id": CASCADE,
        "trajectory_id": trajectory,
        "used_non_gemini_model": "true",
    }
    prefix, cascade, millis, request_trajectory, step = str(body["requestId"]).split("/")
    assert (prefix, cascade, request_trajectory, step) == ("agent", CASCADE, trajectory, "3")
    assert millis.isdigit()
    assert body["model"] == "gemini-3.8-flash-high"
    assert (body["userAgent"], body["requestType"]) == ("antigravity", "agent")
    assert inner["sessionId"] == "-3750763034362895579"


def test_trajectory_is_stable_within_a_turn_and_advances_with_the_next_user_message() -> None:
    first = _envelope(_request(USER))["request"]["labels"]
    continued = _envelope(_request(USER, CALL, RESULT))["request"]["labels"]
    next_turn = _envelope(_request(USER, CALL, RESULT, ANSWER, USER))["request"]["labels"]

    assert first["trajectory_id"] == continued["trajectory_id"]
    assert first["request_id"].endswith("-0")
    assert next_turn["trajectory_id"] != first["trajectory_id"]
    assert next_turn["request_id"] == f"{next_turn['trajectory_id']}-0"
    assert next_turn["last_step_index"] == "4"
    assert uuid.UUID(str(next_turn["trajectory_id"]))


def test_claude_and_gemini_share_the_label_set_without_claude_history() -> None:
    claude = _envelope(_request(USER), CLAUDE)["request"]["labels"]
    gemini = _envelope(_request(USER), GEMINI)["request"]["labels"]

    assert list(claude) == list(gemini)
    assert not {"used_claude", "used_claude_conservative"} & set(claude)
    assert claude["used_non_gemini_model"] == gemini["used_non_gemini_model"] == "true"
    assert claude["model_enum"] == "MODEL_PLACEHOLDER_M905"


def test_cascade_is_deterministic_per_client_and_conversation() -> None:
    assert cascade_id("key-1", "conversation-1") == CASCADE
    assert cascade_id("key-2", "conversation-1") != CASCADE
    assert cascade_id("key-1", "conversation-2") != CASCADE
    assert uuid.UUID(CASCADE).version == 5
