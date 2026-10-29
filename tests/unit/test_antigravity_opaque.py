from __future__ import annotations

import pytest
from cryptography.fernet import Fernet

from app.core.crypto import TokenEncryptor
from app.core.openai.exceptions import ClientPayloadError
from app.modules.antigravity.opaque import (
    PREFIX,
    AntigravityOpaqueState,
    ThoughtScope,
    has_antigravity_replay,
    is_sealed,
    omit_antigravity_replay,
)

OPAQUE = AntigravityOpaqueState(TokenEncryptor(key=Fernet.generate_key()))
SCOPE = ThoughtScope("src-1", "project-1", "gemini-3.8-flash", False, "client-1")


def test_sealed_thought_round_trips_for_its_client() -> None:
    token = OPAQUE.seal(SCOPE, text="plan", signature="sig-1")
    thought = OPAQUE.open(token, client_scope="client-1", param="input[0]")

    assert token.startswith(PREFIX)
    assert (thought.text, thought.signature, thought.family) == ("plan", "sig-1", "gemini-3.8-flash")
    assert SCOPE.owns(thought)


def test_another_client_cannot_open_a_sealed_thought() -> None:
    token = OPAQUE.seal(SCOPE, text="plan", signature="sig-1")

    with pytest.raises(ClientPayloadError) as error:
        OPAQUE.open(token, client_scope="client-2", param="input[0]")

    assert error.value.code == "invalid_provider_history"


@pytest.mark.parametrize(
    "token",
    [
        PREFIX + "not-a-fernet-token",
        AntigravityOpaqueState(TokenEncryptor(key=Fernet.generate_key())).seal(SCOPE, text="", signature=None),
    ],
    ids=["malformed", "foreign_key"],
)
def test_unreadable_state_is_rejected(token: str) -> None:
    with pytest.raises(ClientPayloadError) as error:
        OPAQUE.open(token, client_scope="client-1", param="input[3]")

    assert (error.value.code, error.value.param) == ("invalid_provider_history", "input[3]")


@pytest.mark.parametrize(
    "other",
    [
        ThoughtScope("src-2", "project-1", "gemini-3.8-flash", False, "client-1"),
        ThoughtScope("src-1", "project-2", "gemini-3.8-flash", False, "client-1"),
        ThoughtScope("src-1", "project-1", "claude-sonnet-5", True, "client-1"),
    ],
)
def test_signatures_belong_to_their_account_project_and_wire_family(other: ThoughtScope) -> None:
    thought = OPAQUE.open(OPAQUE.seal(SCOPE, text="plan", signature="sig"), client_scope="client-1", param="p")

    assert not other.owns(thought)


def test_same_wire_family_shares_signatures_across_tiers() -> None:
    thought = OPAQUE.open(OPAQUE.seal(SCOPE, text="plan", signature="sig"), client_scope="client-1", param="p")

    assert ThoughtScope("src-1", "project-1", "gemini-4-argon", False, "client-1").owns(thought)


def test_native_history_omits_only_antigravity_reasoning() -> None:
    sealed = {"type": "reasoning", "encrypted_content": OPAQUE.seal(SCOPE, text="", signature="s")}
    openai = {"type": "reasoning", "encrypted_content": "gAAAA-openai"}
    message = {"type": "message", "role": "user", "content": "hi"}

    assert is_sealed(sealed) and not is_sealed(openai) and not is_sealed(message)
    assert has_antigravity_replay([message, sealed])
    assert not has_antigravity_replay([message, openai])
    assert omit_antigravity_replay([message, sealed, openai]) == [message, openai]
