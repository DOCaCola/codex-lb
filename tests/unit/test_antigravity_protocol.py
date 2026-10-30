from __future__ import annotations

import json
from typing import Any

import pytest
from cryptography.fernet import Fernet

from app.core.crypto import TokenEncryptor
from app.core.openai.exceptions import ClientPayloadError
from app.modules.antigravity.constants import SKIP_SIGNATURE
from app.modules.antigravity.opaque import AntigravityOpaqueState, ThoughtScope
from app.modules.antigravity.protocol import SENSITIVE_WORDS, obfuscate, project_responses
from app.modules.antigravity.schemas import CatalogFamily
from app.modules.antigravity.tool_names import google_wire_name

OPAQUE = AntigravityOpaqueState(TokenEncryptor(key=Fernet.generate_key()))
GEMINI = CatalogFamily(
    id="gemini-3.8-flash",
    display_name="Gemini 3.8 Flash",
    tiers={"low": "gemini-3.8-flash-low", "high": "gemini-3.8-flash-high"},
    api_provider="API_PROVIDER_GOOGLE_GEMINI",
    quota_family="gemini",
    max_output_tokens=65_536,
    supports_thinking=True,
)
CLAUDE = CatalogFamily(
    id="claude-sonnet-5",
    display_name="Claude Sonnet 5",
    api_provider="API_PROVIDER_ANTHROPIC_VERTEX",
    quota_family="claude",
    max_output_tokens=64_000,
    supports_thinking=True,
)
SHELL = {
    "type": "function",
    "name": "shell",
    "description": "Run a command",
    "parameters": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]},
}


def _scope(family: CatalogFamily, source_id: str = "src-1") -> ThoughtScope:
    return ThoughtScope(source_id, "project-1", family.id, family.anthropic_wire, "client-1")


def _project(payload: dict[str, Any], family: CatalogFamily = GEMINI, **options: Any):
    return project_responses(
        payload,
        family=family,
        max_output_tokens=family.max_output_tokens or 1,
        scope=_scope(family),
        opaque=OPAQUE,
        **options,
    )


def _tool_turn(family: CatalogFamily, *, signer: ThoughtScope | None) -> dict[str, Any]:
    reasoning = (
        [{"type": "reasoning", "encrypted_content": OPAQUE.seal(signer, text="plan", signature="sig-1")}]
        if signer is not None
        else []
    )
    return {
        "instructions": "Be brief.",
        "tools": [SHELL],
        "input": [
            {"role": "user", "content": "list files"},
            *reasoning,
            {"type": "function_call", "call_id": "call_1", "name": "shell", "arguments": json.dumps({"command": "ls"})},
            {"type": "function_call_output", "call_id": "call_1", "output": "a.txt"},
        ],
    }


def test_basic_request_matches_the_native_wire_image() -> None:
    projection = _project({"instructions": "Use the Claude Agent SDK.", "input": "hello"})
    request = projection.request
    assert request["contents"] == [{"role": "user", "parts": [{"text": "hello"}]}]
    assert request["systemInstruction"] == {"role": "user", "parts": [{"text": obfuscate("Use the Claude Agent SDK.")}]}
    assert "\u200b" in obfuscate("Claude Agent SDK")
    assert request["generationConfig"] == {
        "maxOutputTokens": 65_536,
        "thinkingConfig": {"includeThoughts": True, "thinkingBudget": -1},
    }
    assert "tools" not in request
    assert "toolConfig" not in request


def test_system_instruction_hides_every_harness_fingerprint() -> None:
    instructions = (
        "Built on the Claude Agent SDK.\n<system-conventions>\nRFC 2119 keywords apply.\n</system-conventions>\n"
        "system_conventions system-directive system_directive"
    )
    projection = _project({"instructions": instructions, "input": "Claude Agent SDK and RFC 2119"})
    system = projection.request["systemInstruction"]["parts"][0]["text"]
    for word in SENSITIVE_WORDS:
        assert word.lower() not in system.lower()
    assert system.replace("\u200b", "") == instructions
    assert projection.request["contents"][0]["parts"][0]["text"] == "Claude Agent SDK and RFC 2119"


def test_gemini_tool_cycle_restores_its_own_signature_on_the_call() -> None:
    projection = _project(_tool_turn(GEMINI, signer=_scope(GEMINI)))
    contents = projection.request["contents"]
    assert [content["role"] for content in contents] == ["user", "model", "model"]
    thought, call = contents[1]["parts"]
    assert thought == {"text": "plan", "thought": True}
    assert call["thoughtSignature"] == "sig-1"
    assert call["functionCall"] == {"id": "call_1", "name": "shell", "args": {"command": "ls"}}
    assert contents[2]["parts"] == [
        {"functionResponse": {"id": "call_1", "name": "shell", "response": {"output": "a.txt"}}}
    ]
    assert projection.restored == 1
    assert projection.request["tools"][0]["functionDeclarations"][0]["name"] == "shell"


def test_foreign_or_unrestored_signatures_use_the_validator_sentinel() -> None:
    foreign = _project(_tool_turn(GEMINI, signer=_scope(GEMINI, source_id="src-other")))
    assert foreign.request["contents"][1]["parts"][-1]["thoughtSignature"] == SKIP_SIGNATURE
    assert foreign.sentinels == 1
    unsigned = _project(_tool_turn(GEMINI, signer=_scope(GEMINI)), restore_signatures=False)
    assert unsigned.request["contents"][1]["parts"][-1]["thoughtSignature"] == SKIP_SIGNATURE


def test_replayed_args_and_declared_properties_follow_go_map_order() -> None:
    # The CLI re-encodes call args as map[string]any: byte order at every depth, unknown keys kept.
    tool = {
        "type": "function",
        "name": "probe",
        "parameters": {
            "type": "object",
            "properties": {"zeta": {"type": "string"}, "Alpha": {"type": "object"}, "_under": {"type": "boolean"}},
        },
    }
    args = {"zeta": "z", "query": "q", "Alpha": {"y": 1, "b": [{"d": 1, "c": 2}], "B": 0}, "_under": True}
    projection = _project(
        {
            "tools": [tool],
            "input": [
                {"role": "user", "content": "probe"},
                {"type": "function_call", "call_id": "call_1", "name": "probe", "arguments": json.dumps(args)},
                {"type": "function_call_output", "call_id": "call_1", "output": "done"},
            ],
        }
    )
    call = projection.request["contents"][1]["parts"][-1]["functionCall"]
    assert json.dumps(call["args"], separators=(",", ":")) == (
        '{"Alpha":{"B":0,"b":[{"c":2,"d":1}],"y":1},"_under":true,"query":"q","zeta":"z"}'
    )
    declaration = projection.request["tools"][0]["functionDeclarations"][0]
    assert list(declaration["parameters"]["properties"]) == ["Alpha", "_under", "zeta"]


def test_claude_on_antigravity_answers_tools_as_user_and_keeps_signed_thinking() -> None:
    projection = _project(_tool_turn(CLAUDE, signer=_scope(CLAUDE)), CLAUDE)
    contents = projection.request["contents"]
    assert [content["role"] for content in contents] == ["user", "model", "user"]
    assert contents[1]["parts"][0] == {"text": "plan", "thought": True, "thoughtSignature": "sig-1"}
    assert "thoughtSignature" not in contents[1]["parts"][1]
    assert "thinkingConfig" in projection.request["generationConfig"]


def test_claude_open_turn_without_signed_thinking_disables_thinking() -> None:
    projection = _project(_tool_turn(CLAUDE, signer=_scope(GEMINI)), CLAUDE)
    assert projection.thinking_disabled
    assert all(part.get("thought") is not True for part in projection.request["contents"][1]["parts"])
    assert "thinkingConfig" not in projection.request["generationConfig"]


def test_model_tail_and_head_are_wrapped_in_user_turns() -> None:
    projection = _project({"input": [{"role": "assistant", "content": "earlier answer"}]})
    assert projection.request["contents"] == [
        {"role": "user", "parts": [{"text": "(continue)"}]},
        {"role": "model", "parts": [{"text": "earlier answer"}]},
        {"role": "user", "parts": [{"text": "(continue)"}]},
    ]


def test_tool_choice_projection() -> None:
    required = _project({"input": "x", "tools": [SHELL], "tool_choice": "required"})
    assert required.request["toolConfig"] == {"functionCallingConfig": {"mode": "ANY"}}
    named = _project({"input": "x", "tools": [SHELL], "tool_choice": {"type": "function", "name": "shell"}})
    assert named.request["toolConfig"] == {"functionCallingConfig": {"mode": "ANY", "allowedFunctionNames": ["shell"]}}
    none = _project({"input": "x", "tools": [SHELL], "tool_choice": "none"})
    assert "tools" not in none.request


def test_namespaced_tools_get_reversible_wire_names() -> None:
    namespace = {"type": "namespace", "name": "mcp__files", "tools": [{**SHELL, "name": "read.file"}]}
    projection = _project({"input": "x", "tools": [namespace]})
    [declaration] = projection.request["tools"][0]["functionDeclarations"]
    identity = projection.tools.resolve(declaration["name"])
    assert identity is not None
    assert identity.name == "read.file"
    assert declaration["name"] != "read.file"


def test_google_wire_names_pass_valid_names_unchanged() -> None:
    assert google_wire_name("apply_patch") == "apply_patch"
    encoded = google_wire_name("mcp.files/read")
    assert len(encoded) <= 64
    assert encoded == google_wire_name("mcp.files/read")
    assert encoded.replace("_", "").isalnum()
    assert len(google_wire_name("x" * 100)) <= 64


@pytest.mark.parametrize(
    ("payload", "param"),
    [
        ({"input": "x", "previous_response_id": "resp_1"}, "previous_response_id"),
        ({"input": "x", "max_output_tokens": 100_000}, "max_output_tokens"),
        ({"input": "x", "service_tier": "priority"}, "service_tier"),
        ({"input": "x", "text": {"verbosity": "low"}}, "text.verbosity"),
        (
            {
                "input": [{"type": "function_call", "call_id": "c", "name": "shell", "arguments": "{}"}],
                "tools": [SHELL],
            },
            "input",
        ),
    ],
)
def test_unsupported_requests_fail_explicitly(payload: dict[str, Any], param: str) -> None:
    with pytest.raises(ClientPayloadError) as raised:
        _project(payload)
    assert raised.value.param == param


def test_reasoning_from_another_client_is_rejected() -> None:
    other = ThoughtScope("src-1", "project-1", GEMINI.id, False, "client-2")
    payload = _tool_turn(GEMINI, signer=other)
    with pytest.raises(ClientPayloadError) as raised:
        _project(payload)
    assert raised.value.code == "invalid_provider_history"


def test_structured_output_uses_json_schema() -> None:
    schema = {"type": "object", "properties": {"ok": {"type": "boolean"}}}
    projection = _project({"input": "x", "text": {"format": {"type": "json_schema", "name": "r", "schema": schema}}})
    assert projection.request["generationConfig"]["responseMimeType"] == "application/json"
    assert projection.request["generationConfig"]["responseJsonSchema"] == schema
