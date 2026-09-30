import json
from copy import deepcopy
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.core.crypto import TokenEncryptor
from app.core.openai.models import OpenAIResponsePayload
from app.core.openai.requests import ResponsesRequest, sanitize_native_responses_input
from app.db.session import SessionLocal
from app.modules.api_keys.repository import ApiKeysRepository
from app.modules.api_keys.service import ApiKeysService
from app.modules.claude.opaque import ClaudeOpaqueState, OpaqueScope
from app.modules.proxy import service as proxy_service
from app.modules.proxy._service.websocket import mixin as websocket_mixin
from app.modules.proxy._service.websocket.replay_store import ReplayScope
from tests.integration.test_proxy_affinity_observation import _import_synthetic_account
from tests.integration.test_proxy_affinity_websocket_observation import SyntheticUpstream, seed_account
from tests.unit.test_proxy_utils import _repo_factory, _RequestLogsRecorder

pytestmark = pytest.mark.integration

HEADERS = {"session_id": "native-provider-history"}


def history(kind="thinking", *, client_scope="anonymous"):
    opaque = ClaudeOpaqueState(TokenEncryptor())
    token = opaque.encode(
        OpaqueScope("claude-source", "anthropic/claude-opus-5-5", client_scope, HEADERS["session_id"]),
        {"type": kind, "thinking": "Preserved Opus context", "signature": "signed"},
    )
    return [
        {"type": "reasoning", "id": "resp_msg_011CfZMoJxcBo6bvenx5qRj2_0", "summary": [], "encrypted_content": token},
        {"type": "function_call", "id": "resp_msg_call", "call_id": "call_1", "name": "lookup", "arguments": "{}"},
        {"type": "function_call_output", "call_id": "call_1", "output": "retained result"},
        {"role": "user", "content": "Continue on Sol"},
    ]


def assert_native(items):
    assert items[0] == {"type": "reasoning", "summary": [{"type": "summary_text", "text": "Preserved Opus context"}]}
    assert items[1]["call_id"] == items[2]["call_id"] == "call_1"
    assert items[2]["output"] == "retained result"
    assert "claude-v1." not in str(items)
    assert "resp_msg" not in str(items)


@pytest.mark.parametrize("path", ["/v1/responses", "/backend-api/codex/responses", "/v1/responses/compact"])
async def test_public_native_http_and_compaction_project_claude_history(async_client, monkeypatch, path):
    await _import_synthetic_account(async_client)
    captured = []

    async def stream(payload, *args, **kwargs):
        captured.append(sanitize_native_responses_input(payload.to_payload())["input"])
        yield 'data: {"type":"response.completed","response":{"id":"resp_native","status":"completed","output":[]}}\n\n'

    async def compact(payload, *args, **kwargs):
        captured.append(sanitize_native_responses_input(payload.to_payload())["input"])
        return OpenAIResponsePayload.model_validate({"output": []})

    monkeypatch.setattr(proxy_service, "core_stream_responses", stream)
    monkeypatch.setattr(proxy_service, "core_compact_responses", compact)
    original = history()
    response = await async_client.post(
        path,
        headers=HEADERS,
        json={"model": "gpt-6.1-sol", "instructions": "Continue", "input": original, "stream": True},
    )
    assert response.status_code == 200
    assert len(captured) == 1
    assert_native(captured[0])
    assert original[0]["encrypted_content"].startswith("claude-v1.")


@pytest.mark.parametrize("kind", ["redacted_thinking", "web_search"])
async def test_public_native_nonportable_history_never_dispatches(async_client, monkeypatch, kind):
    await _import_synthetic_account(async_client)
    sent = AsyncMock()
    monkeypatch.setattr(proxy_service, "core_compact_responses", sent)
    response = await async_client.post(
        "/v1/responses/compact",
        headers=HEADERS,
        json={"model": "gpt-6.1-sol", "input": history(kind)},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "nonportable_provider_history"
    assert response.json()["error"]["param"] == "input[0]"
    sent.assert_not_awaited()


async def prepare_websocket(service, payload):
    return await service._prepare_websocket_response_create_request(
        payload,
        headers=HEADERS,
        codex_session_affinity=False,
        openai_cache_affinity=True,
        sticky_threads_enabled=False,
        openai_cache_affinity_max_age_seconds=300,
        api_key=None,
    )


@pytest.mark.parametrize("retained", [False, True])
async def test_native_websocket_expands_before_projection_and_retains_original(async_client, monkeypatch, retained):
    service = proxy_service.ProxyService(_repo_factory(_RequestLogsRecorder()))
    monkeypatch.setattr(service, "_refresh_websocket_api_key_policy", AsyncMock(return_value=None))
    monkeypatch.setattr(service, "_reserve_websocket_api_key_usage", AsyncMock(return_value=None))
    original = history()
    untouched = deepcopy(original)
    payload = {"model": "gpt-6.1-sol", "input": original}
    if retained:
        await service._http_fallback_replay_store.remember(
            ReplayScope(None, HEADERS["session_id"]),
            "resp_claude_switch",
            json.dumps({"model": "anthropic/claude-opus-5-5", "input": []}),
            original,
            "claude-source",
        )
        payload = {"model": "gpt-6.1-sol", "previous_response_id": "resp_claude_switch", "input": []}
    prepared = await prepare_websocket(service, payload)
    assert_native(json.loads(prepared.text_data)["input"])
    assert prepared.request_state.http_replay_input == original
    assert original == untouched
    if retained:
        stored = await service._http_fallback_replay_store.load(
            ReplayScope(None, HEADERS["session_id"]), "resp_claude_switch"
        )
        assert stored.output == untouched


async def test_source_owned_websocket_keeps_claude_state(async_client, monkeypatch):
    service = proxy_service.ProxyService(_repo_factory(_RequestLogsRecorder()))
    monkeypatch.setattr(service, "_refresh_websocket_api_key_policy", AsyncMock(return_value=None))
    monkeypatch.setattr(service, "_reserve_websocket_api_key_usage", AsyncMock(return_value=None))
    monkeypatch.setattr(websocket_mixin, "responses_model_is_source_owned", AsyncMock(return_value=True))
    original = history()
    prepared = await prepare_websocket(service, {"model": "anthropic/claude-opus-5-5", "input": original})
    assert json.loads(prepared.text_data)["input"][0]["encrypted_content"] == original[0]["encrypted_content"]


def test_http_bridge_request_preparation_projects_native_history():
    service = proxy_service.ProxyService(_repo_factory(_RequestLogsRecorder()))
    payload = ResponsesRequest.model_validate({"model": "gpt-6.1-sol", "instructions": "Continue", "input": history()})
    _, frame = service._prepare_http_bridge_request(payload, HEADERS, api_key=None, api_key_reservation=None)
    assert_native(json.loads(frame)["input"])
    assert payload.input[0]["encrypted_content"].startswith("claude-v1.")


@pytest.mark.parametrize("kind", ["thinking", "redacted_thinking", "web_search", "wrong_client"])
def test_public_keyed_websocket_native_switch_preserves_or_rejects_history(app_instance, monkeypatch, kind):
    captured = []
    auth_scopes = []
    authenticate = ClaudeOpaqueState.authenticate

    def authenticate_recorded(self, token, **kwargs):
        auth_scopes.append(kwargs)
        return authenticate(self, token, **kwargs)

    monkeypatch.setattr(ClaudeOpaqueState, "authenticate", authenticate_recorded)

    class RecordingUpstream(SyntheticUpstream):
        async def send_text(self, text):
            captured.append(json.loads(text))
            await super().send_text(text)

    async def connect(*args, **kwargs):
        return RecordingUpstream()

    async def make_history(key):
        async with SessionLocal() as session:
            api_key = await ApiKeysService(ApiKeysRepository(session)).validate_key(key)
        return history(
            "thinking" if kind == "wrong_client" else kind,
            client_scope="another-key" if kind == "wrong_client" else api_key.id,
        )

    monkeypatch.setattr(proxy_service, "connect_responses_websocket", connect)
    with TestClient(app_instance, client=("127.0.0.1", 50000)) as client:
        key = client.portal.call(seed_account)
        assert client.put("http://localhost/api/settings", json={"apiKeyAuthEnabled": True}).status_code == 200
        original = client.portal.call(make_history, key)
        with client.websocket_connect(
            "ws://localhost/backend-api/codex/responses",
            headers={**HEADERS, "authorization": f"Bearer {key}"},
        ) as websocket:
            websocket.send_json({"type": "response.create", "model": "gpt-6.1-sol", "input": original})
            event = websocket.receive_json()
            assert auth_scopes[-1]["conversation_id"] == HEADERS["session_id"], auth_scopes
            if kind == "thinking":
                assert event["type"] == "response.created", event
                assert websocket.receive_json()["type"] == "response.completed"
            else:
                assert event["type"] == "error", event
                assert event["error"]["code"] == (
                    "invalid_provider_history" if kind == "wrong_client" else "nonportable_provider_history"
                )
                assert event["error"]["param"] == "input[0]"
        assert client.portal.call(app_instance.state.proxy_service.drain_persistence_tasks, 5.0)
    if kind == "thinking":
        assert len(captured) == 1
        assert_native(captured[0]["input"])
    else:
        assert captured == []
