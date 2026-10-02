from __future__ import annotations

import json
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from typing import Any
from unittest.mock import AsyncMock

import pytest

import app.core.clients.proxy as proxy_module
import app.core.clients.proxy_websocket as ws_client
from app.core.clients.responses_transport import utf8_size
from app.core.config.settings import Settings
from app.core.openai.requests import ResponsesRequest
from app.core.types import JsonValue
from app.core.utils.encoded_json import EncodedJsonObject, decode_json_object, encode_json_object


def _compact(value: object) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"))


@pytest.mark.parametrize(
    "text",
    [
        "{}",
        " \n{ } \t",
        '{"a":1,"b":[true,false,null],"c":{"d":"\\u00e9\\n"},"e":1.5e3,"f":-0}',
        '{ "input" : [ {"role" : "user"} ] , "model":"m" }',
        '{"k":1,"k":2}',
        '{"\u00fc":"\u00df"}',
    ],
)
def test_decode_matches_json_loads_and_records_member_text(text: str) -> None:
    decoded = decode_json_object(text)

    assert decoded.values == json.loads(text)
    assert decoded.encoded.keys() == decoded.values.keys()
    for key, encoded in decoded.encoded.items():
        assert json.loads(encoded) == decoded.values[key]


@pytest.mark.parametrize(
    "text",
    ["", "[]", '"a"', '{"a":1} x', '{"a" 1}', '{"a":1,}', "{a:1}", '{"a":1 "b":2}', '{"a":}', '{"a":1', "{,}"],
)
def test_decode_rejects_anything_that_is_not_one_json_object(text: str) -> None:
    with pytest.raises(json.JSONDecodeError):
        decode_json_object(text)


def test_encode_without_source_is_compact_ascii_json() -> None:
    payload: dict[str, JsonValue] = {"a": [1, True, None], "\u00e9": "\u00df"}

    assert encode_json_object(payload) == _compact(payload)


def test_encode_reuses_unchanged_member_text_and_encodes_changed_members() -> None:
    source = decode_json_object('{"type":"response.create","input":[ 1, {"x" : 2} ],"stream":false}')
    payload = dict(source.values)
    payload.pop("type")
    payload["stream"] = True
    payload["model"] = "m"

    assert encode_json_object(payload, source) == '{"input":[ 1, {"x" : 2} ],"stream":true,"model":"m"}'


def test_encode_reencodes_a_member_whose_nested_value_changed() -> None:
    source = decode_json_object('{"input":[ 1, {"x" : 2} ]}')
    payload: dict[str, JsonValue] = {"input": [1, {"x": 3}]}

    assert encode_json_object(payload, source) == '{"input":[1,{"x":3}]}'


def test_encode_keeps_json_types_distinct() -> None:
    source = decode_json_object('{"a":1,"b":0.0,"c":[false],"d":{"e":1}}')
    payload: dict[str, JsonValue] = {"a": True, "b": 0, "c": [0], "d": {"e": 1.0}}

    assert encode_json_object(payload, source) == _compact(payload)


def test_encode_reuse_preserves_non_ascii_member_text() -> None:
    source = decode_json_object('{"text":"gr\u00fc\u00df","n":1}')

    body = encode_json_object({"text": "gr\u00fc\u00df", "n": 2}, source)

    assert body == '{"text":"gr\u00fc\u00df","n":2}'
    assert json.loads(body.encode("utf-8")) == {"text": "gr\u00fc\u00df", "n": 2}


@pytest.mark.parametrize("text", ["", "abc", "\u00e9", "\U0001f600x"])
def test_utf8_size_matches_encoded_length(text: str) -> None:
    assert utf8_size(text) == len(text.encode("utf-8"))


class _Chunks:
    def __init__(self, chunks: Sequence[bytes]) -> None:
        self._chunks = list(chunks)

    async def _iterate(self) -> AsyncIterator[bytes]:
        for chunk in self._chunks:
            yield chunk

    def iter_chunked(self, size: int) -> AsyncIterator[bytes]:
        del size
        return self._iterate()


class _NativeResponse:
    status = 200
    headers: dict[str, str] = {}

    def __init__(self) -> None:
        self.content = _Chunks([b'data: {"type":"response.completed","response":{"id":"resp_http"}}\n\n'])

    async def __aenter__(self) -> _NativeResponse:
        return self

    async def __aexit__(self, *_args: object) -> None:
        return None

    async def aclose(self) -> None:
        return None


class _NativeClient:
    def __init__(self) -> None:
        self.bodies: list[bytes] = []

    async def request(self, request: Any) -> _NativeResponse:
        self.bodies.append(request.body)
        return _NativeResponse()


@asynccontextmanager
async def _unused_session(session: Any = None) -> AsyncIterator[Any]:
    # The native helper carries every request here; no Python session is used.
    yield object()


_IMAGE = {"type": "input_image", "image_url": "data:image/png;base64," + "QUJD" * 512}
_LITE_TOOLS = {"type": "additional_tools", "role": "developer", "tools": []}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "frame",
    [
        pytest.param(
            {
                "type": "response.create",
                "model": "gpt-6-astra",
                "instructions": "base",
                "input": [
                    {"role": "user", "content": [_IMAGE, {"type": "input_text", "text": "gr\u00fc\u00df"}]},
                    {"type": "function_call", "call_id": "c1", "name": "shell", "arguments": "{}"},
                    {"type": "function_call_output", "call_id": "c1", "output": "ok"},
                ],
                "store": False,
                "client_metadata": {"x-codex-installation-id": "install"},
            },
            id="history-unchanged",
        ),
        pytest.param(
            {
                "type": "response.create",
                "model": "gpt-6-astra",
                "instructions": "base",
                "input": [
                    {"role": "developer", "content": [{"type": "input_text", "text": "lifted"}]},
                    {"role": "user", "content": [_IMAGE]},
                ],
                "store": False,
            },
            id="history-normalized",
        ),
        pytest.param(
            {
                "type": "response.create",
                "model": "gpt-6-astra",
                "instructions": "",
                "input": [_LITE_TOOLS, {"role": "user", "content": [_IMAGE]}],
                "store": False,
                "client_metadata": {
                    proxy_module.CODEX_RESPONSES_LITE_WEBSOCKET_METADATA_KEY: "true",
                    "x-codex-installation-id": "install",
                },
            },
            id="responses-lite",
        ),
    ],
)
async def test_http_handoff_sends_the_body_a_full_serialization_would_send(
    monkeypatch: pytest.MonkeyPatch, frame: dict[str, Any]
) -> None:
    settings = Settings()
    native_client = _NativeClient()
    sources: list[EncodedJsonObject | None] = []

    def recording_encode(payload: Any, source: EncodedJsonObject | None = None) -> str:
        sources.append(source)
        return encode_json_object(payload, source)

    monkeypatch.setattr(ws_client, "get_settings", lambda: settings)
    monkeypatch.setattr(proxy_module, "get_settings", lambda: settings)
    monkeypatch.setattr(ws_client, "_connect_upstream_websocket", AsyncMock())
    monkeypatch.setattr(proxy_module, "UPSTREAM_RESPONSE_CREATE_MAX_BYTES", 1024)
    monkeypatch.setattr(proxy_module, "discover_native_egress_client", lambda: native_client)
    monkeypatch.setattr(proxy_module, "lease_http_session", _unused_session)
    monkeypatch.setattr(proxy_module, "encode_json_object", recording_encode)
    text = _compact(frame)

    transport = await ws_client.connect_responses_websocket(
        {"session_id": "session"},
        "account-token",
        "account-id",
        initial_request_text=text,
        allow_direct_egress=True,
    )
    try:
        await transport.send_text(text)
        completed = await transport.receive()
    finally:
        await transport.close()
    assert completed.text is not None
    assert json.loads(completed.text)["type"] == "response.completed"

    reference = {key: value for key, value in json.loads(text).items() if key != "type"}
    reference["stream"] = True
    async for _event in proxy_module.stream_responses(
        ResponsesRequest.model_validate(reference),
        {"session_id": "session"},
        "account-token",
        "account-id",
        upstream_stream_transport_override="http",
        allow_direct_egress=True,
        enforce_openai_sdk_contract=False,
    ):
        pass

    handoff_body, reference_body = native_client.bodies
    assert sources[0] is not None
    assert sources[1] is None
    assert handoff_body == reference_body
    assert json.loads(handoff_body)["stream"] is True
    assert "type" not in json.loads(handoff_body)
