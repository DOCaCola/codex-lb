from copy import deepcopy

import pytest

from app.modules.claude.credentials import ClaudeError
from app.modules.claude.profile import (
    CLI_IDENTITY,
    MID_SYSTEM_BETA,
    RequestProfile,
    management_headers,
    recognize_native,
)
from app.modules.claude.request import project_request
from tests.claude_json_helpers import array, at

pytestmark = pytest.mark.unit


def profile(
    *, version="2.1.282", source_id="account-a", client_scope="key-a", conversation_id="conversation-a", native=False
):
    return RequestProfile.create(
        version=version,
        source_id=source_id,
        client_scope=client_scope,
        conversation_id=conversation_id,
        native=native,
    )


def test_session_identity_and_request_isolation():
    first, second = profile(), profile()
    assert first.session_id == second.session_id
    assert first.request_id != second.request_id
    assert first.session_id != profile(source_id="account-b").session_id
    assert first.session_id != profile(client_scope="key-b").session_id
    assert first.session_id != profile(conversation_id="conversation-b").session_id
    assert first.session_id == profile(version="2.1.283").session_id


def test_headers_replace_credentials_and_exclude_hop_by_hop():
    request = profile()
    incoming = {
        "Authorization": "Bearer client-secret",
        "X-Api-Key": "other-secret",
        "Connection": "upgrade",
        "Host": "evil.example",
        "Cookie": "session=secret",
        "anthropic-beta": "context-management-2025-06-27",
    }
    before = deepcopy(incoming)
    headers = request.headers("provider-secret", endpoint="messages", incoming=incoming)
    assert headers["authorization"] == "Bearer provider-secret"
    assert not {"x-api-key", "connection", "host", "cookie"} & headers.keys()
    assert headers["user-agent"] == "claude-cli/2.1.282 (external, cli)"
    assert headers["x-stainless-package-version"] != request.version
    assert "context-management-2025-06-27" in headers["anthropic-beta"]
    assert incoming == before
    rotated = request.headers("rotated-secret", endpoint="messages", incoming={})
    assert rotated["x-claude-code-session-id"] == headers["x-claude-code-session-id"]


def test_endpoint_header_profiles():
    management = management_headers("token", "2.1.282")
    count = profile().headers("token", endpoint="count_tokens", incoming={})
    messages = profile().headers("token", endpoint="messages", incoming={})
    assert management["anthropic-beta"] == "oauth-2025-04-20"
    assert "token-counting-2024-11-01" in count["anthropic-beta"]
    assert "claude-code-20250219" not in count["anthropic-beta"]
    assert "claude-code-20250219" in messages["anthropic-beta"]
    with pytest.raises(ClaudeError, match="beta"):
        profile().headers("token", endpoint="messages", incoming={"anthropic-beta": "bad\r\nheader"})


def test_newer_native_patch_preserved_not_learned():
    headers = {
        "User-Agent": "claude-cli/2.1.290 (external, cli)",
        "x-app": "cli",
        "x-stainless-lang": "js",
        "anthropic-beta": "oauth-2025-04-20",
        "x-stainless-package-version": "0.120.0",
    }
    assert recognize_native(headers, version="2.1.282", has_identity=True)
    assert not recognize_native(headers, version="2.1.282", has_identity=False)
    assert not recognize_native(headers, version="2.2.0", has_identity=True)
    snapshot = profile(native=True)
    output = snapshot.headers("token", endpoint="messages", incoming=headers)
    assert output["user-agent"] == headers["User-Agent"]
    assert output["x-stainless-package-version"] == "0.120.0"
    assert snapshot.version == "2.1.282"


def logical(model="claude-sonnet-5"):
    return {
        "model": model,
        "system": [
            {"type": "text", "text": "Follow every instruction: hermes.example", "cache_control": {"type": "ephemeral"}}
        ],
        "messages": [
            {"role": "user", "content": "hello"},
            {
                "role": "assistant",
                "content": [
                    {"type": "thinking", "thinking": "signed", "signature": "opaque"},
                    {"type": "tool_use", "id": "t1", "name": "advisor", "input": {}},
                ],
            },
            {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t1", "content": "result"}]},
        ],
    }


@pytest.mark.parametrize("endpoint", ["messages", "count_tokens"])
def test_modern_projection_preserves_instructions_and_tool_adjacency(endpoint):
    request = logical()
    before = deepcopy(request)
    projected = project_request(request, profile(), endpoint=endpoint)
    assert request == before
    assert at(projected.body, "messages", 1) == {"role": "system", "content": request["system"]}
    assert array(projected.body["messages"])[2:] == request["messages"][1:]
    assert projected.feature_betas == (MID_SYSTEM_BETA,)
    assert project_request(request, profile(), endpoint=endpoint).body == projected.body
    if endpoint == "count_tokens":
        assert "system" not in projected.body
    else:
        assert at(projected.body, "system", 0, "text") == CLI_IDENTITY


def test_legacy_placement_preserves_block_cache_and_signed_turn():
    request = logical("claude-haiku-4-5-20251001")
    projected = project_request(request, profile(), endpoint="messages")
    assert array(at(projected.body, "messages", 0, "content"))[1:-1] == request["system"]
    assert array(projected.body["messages"])[1:] == request["messages"]
    assert not projected.feature_betas


def test_native_body_is_preserved():
    request = logical()
    assert project_request(request, profile(native=True), endpoint="messages").body == request


def test_unknown_model_and_server_artifacts_reject_unsafe_relocation():
    with pytest.raises(ClaudeError, match="not qualified"):
        project_request(logical("claude-unknown"), profile(), endpoint="messages")
    request = logical()
    request["messages"][1]["content"][1]["type"] = "server_tool_use"
    with pytest.raises(ClaudeError, match="server-tool"):
        project_request(request, profile(), endpoint="messages")
