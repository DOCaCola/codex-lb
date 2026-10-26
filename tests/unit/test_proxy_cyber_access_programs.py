"""Security-work refusal detection and per-account cyber access programs."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

import pytest

from app.core.clients.proxy import UpstreamAccountStamp, apply_cyber_access_program, apply_upstream_account_stamp
from app.core.types import JsonValue
from app.modules.proxy import capability_routing
from app.modules.proxy import service as proxy_service
from app.modules.proxy._service.http_bridge.request_submit import _text_without_account_stamp
from app.modules.proxy.replay_safety import responses_payload_is_account_neutral_fresh_replay


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        ("cyber_policy", True),
        ("security_work_authorization_required", True),
        ("invalid_request_error", False),
        (None, False),
    ],
)
def test_security_work_refusal_is_recognized_by_code(code: str | None, expected: bool) -> None:
    assert proxy_service._is_security_work_authorization_required_error(code) is expected


class _Registry:
    def __init__(self, programs: frozenset[str]) -> None:
        self._programs = programs

    def cyber_access_programs_for_account(self, slug: str, account_id: str) -> frozenset[str]:
        assert (slug, account_id) == ("gpt-6-astra", "acc-1")
        return self._programs


@pytest.mark.parametrize(
    ("programs", "authorized", "expected"),
    [
        (frozenset({"standard", "daybreak_blue", "daybreak_red"}), True, "daybreak_blue"),
        (frozenset({"standard", "daybreak_red"}), True, "daybreak_red"),
        (frozenset({"standard", "daybreak_blue"}), False, "standard"),
        (frozenset({"standard"}), True, "standard"),
        (frozenset({"daybreak_blue"}), False, None),
        (frozenset(), True, None),
    ],
)
def test_cyber_access_program_matches_stock_client_selection(
    monkeypatch: pytest.MonkeyPatch,
    programs: frozenset[str],
    authorized: bool,
    expected: str | None,
) -> None:
    monkeypatch.setattr(capability_routing, "get_model_registry", lambda: _Registry(programs))
    account = cast(Any, SimpleNamespace(id="acc-1", security_work_authorized=authorized, codex_installation_id="i-1"))

    assert capability_routing.cyber_access_program_for_account(account, "gpt-6-astra") == expected
    assert capability_routing.upstream_account_stamp(account, "gpt-6-astra") == UpstreamAccountStamp("i-1", expected)


def test_cyber_access_program_requires_a_model() -> None:
    account = cast(Any, SimpleNamespace(id="acc-1", security_work_authorized=True))

    assert capability_routing.cyber_access_program_for_account(account, None) is None


def test_access_program_stamp_replaces_client_value() -> None:
    payload: dict[str, JsonValue] = {"model": "gpt-6-astra", "access_programs": {"cyber": "daybreak_red"}}

    apply_cyber_access_program(payload, "standard")
    assert payload["access_programs"] == {"cyber": "standard"}

    apply_cyber_access_program(payload, None)
    assert "access_programs" not in payload


def test_stamped_access_programs_keep_the_request_account_neutral() -> None:
    payload: dict[str, JsonValue] = {"model": "gpt-6-astra", "input": [], "store": False}
    apply_upstream_account_stamp(payload, UpstreamAccountStamp("i-1", "daybreak_blue"))

    assert payload["access_programs"] == {"cyber": "daybreak_blue"}
    assert responses_payload_is_account_neutral_fresh_replay(payload) is True


def test_bridge_fingerprint_ignores_account_stamp() -> None:
    unstamped = '{"model":"gpt-6-astra","input":[]}'
    stamped = '{"model":"gpt-6-astra","input":[],"access_programs":{"cyber":"standard"}}'

    assert _text_without_account_stamp(stamped) == _text_without_account_stamp(unstamped)
