"""Single-pass request body bookkeeping: input fingerprints and account neutrality."""

from __future__ import annotations

import json
import time

import pytest

from app.core.clients.proxy import CODEX_INSTALLATION_ID_HEADER
from app.core.types import JsonValue
from app.modules.proxy._service.http_bridge.request_submit import _text_with_account_installation_id
from app.modules.proxy._service.response_create import _fingerprint_input_items
from app.modules.proxy._service.support import (
    _inherit_stamped_request_body_account_neutrality,
    _InputFingerprints,
    _record_request_body_account_neutrality,
    _request_body_is_account_neutral_fresh_replay,
    _WebSocketRequestState,
)
from app.modules.proxy._service.websocket.helpers import _install_fresh_replay_body

_ITEMS: list[JsonValue] = [
    {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "é" * index, "z": [1, None]}]}
    for index in range(5)
]


def _request_state() -> _WebSocketRequestState:
    return _WebSocketRequestState(
        request_id="req-single-pass",
        model="gpt-5.4",
        service_tier=None,
        reasoning_effort=None,
        api_key_reservation=None,
        started_at=time.monotonic(),
    )


def _body(client_metadata: JsonValue = None) -> dict[str, JsonValue]:
    body: dict[str, JsonValue] = {
        "type": "response.create",
        "model": "gpt-5.4",
        "input": [{"type": "message", "role": "user", "content": [{"type": "input_text", "text": "hi"}]}],
    }
    if client_metadata is not None:
        body["client_metadata"] = client_metadata
    return body


@pytest.mark.parametrize("prefix_count", range(len(_ITEMS) + 2))
def test_input_fingerprints_match_canonical_fingerprints(prefix_count: int) -> None:
    fingerprints = _InputFingerprints(_ITEMS)

    assert fingerprints.prefix(prefix_count) == _fingerprint_input_items(_ITEMS[:prefix_count])
    assert fingerprints.full() == _fingerprint_input_items(_ITEMS)


def test_input_fingerprints_answer_a_second_prefix_count() -> None:
    fingerprints = _InputFingerprints(_ITEMS)
    fingerprints.prefix(2)

    assert fingerprints.prefix(3) == _fingerprint_input_items(_ITEMS[:3])
    assert _InputFingerprints([]).full() == _fingerprint_input_items([])


def test_recorded_verdict_matches_parsed_verdict() -> None:
    neutral = _body({"x-codex-window-id": "w1"})
    bound = _body({"unknown_key": "v"})
    for payload, expected in ((neutral, True), (bound, False)):
        text = json.dumps(payload, separators=(",", ":"))
        recorded = _request_state()
        recorded.request_text = text
        _record_request_body_account_neutrality(recorded, text, payload)

        assert _request_body_is_account_neutral_fresh_replay(recorded, text) is expected
        assert _request_body_is_account_neutral_fresh_replay(_request_state(), text) is expected


def test_stamped_body_verdict_uses_the_stamped_metadata() -> None:
    # A blank installation id is not account neutral; the stamp replaces it.
    payload = _body({CODEX_INSTALLATION_ID_HEADER: ""})
    text = json.dumps(payload, separators=(",", ":"))
    request_state = _request_state()
    request_state.request_text = text
    _record_request_body_account_neutrality(request_state, text, payload)
    assert _request_body_is_account_neutral_fresh_replay(request_state, text) is False

    stamped = _text_with_account_installation_id(text, "install-1")
    request_state.request_text = stamped
    _inherit_stamped_request_body_account_neutrality(request_state, [(text, stamped)], "install-1")

    assert request_state.body_account_neutrality[-1][0] is stamped
    assert _request_body_is_account_neutral_fresh_replay(request_state, stamped) is True
    assert _request_body_is_account_neutral_fresh_replay(_request_state(), stamped) is True


def test_memo_releases_bodies_the_request_no_longer_holds() -> None:
    request_state = _request_state()
    first = json.dumps(_body(), separators=(",", ":"))
    request_state.request_text = first
    _record_request_body_account_neutrality(request_state, first, _body())

    second = json.dumps(_body({"x-codex-window-id": "w2"}), separators=(",", ":"))
    request_state.request_text = second
    _record_request_body_account_neutrality(request_state, second, _body({"x-codex-window-id": "w2"}))

    assert [entry[0] for entry in request_state.body_account_neutrality] == [second]


def test_fresh_replay_install_keeps_the_client_input_fingerprint() -> None:
    # The next turn's prefix match compares the client's raw input, so the
    # continuity record must keep describing it, not the sanitized fresh body.
    request_state = _request_state()
    request_state.input_item_count = len(_ITEMS)
    request_state.input_full_fingerprint = _fingerprint_input_items(_ITEMS)
    fresh_text = json.dumps(_body(), separators=(",", ":"))

    _install_fresh_replay_body(request_state, fresh_text, account_neutral=True)

    assert request_state.request_text is fresh_text
    assert request_state.input_item_count == len(_ITEMS)
    assert request_state.input_full_fingerprint == _fingerprint_input_items(_ITEMS)
