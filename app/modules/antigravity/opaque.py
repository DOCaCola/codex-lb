"""Authenticated, client-bound Gemini thought state with account and project provenance.

Thought signatures are channel-bound: they verify only on the project and model
family that produced them (CLIProxyAPI signature validation). Codex keeps them
inside encrypted reasoning items, so the adapter can restore them only for the
same account, project and wire family, and other providers never read them.
"""

from __future__ import annotations

from dataclasses import dataclass

from cryptography.fernet import InvalidToken
from pydantic import BaseModel, ValidationError

from app.core.crypto import TokenEncryptor
from app.core.openai.exceptions import ClientPayloadError
from app.core.openai.reasoning import ANTIGRAVITY_REASONING_PREFIX
from app.core.types import JsonValue

PREFIX = ANTIGRAVITY_REASONING_PREFIX


class SealedThought(BaseModel):
    source_id: str
    project_id: str
    # Catalog family id and its wire family; Claude-on-Antigravity signatures are Anthropic's.
    family: str
    anthropic_wire: bool
    client_scope: str
    text: str = ""
    signature: str | None = None


@dataclass(frozen=True)
class ThoughtScope:
    source_id: str
    project_id: str
    family: str
    anthropic_wire: bool
    client_scope: str

    def owns(self, thought: SealedThought) -> bool:
        """Whether this request's channel can verify the thought's signature."""
        return (
            thought.source_id == self.source_id
            and thought.project_id == self.project_id
            and thought.anthropic_wire == self.anthropic_wire
        )


class AntigravityOpaqueState:
    def __init__(self, encryptor: TokenEncryptor) -> None:
        self.encryptor = encryptor

    def seal(self, scope: ThoughtScope, *, text: str, signature: str | None) -> str:
        envelope = SealedThought(
            source_id=scope.source_id,
            project_id=scope.project_id,
            family=scope.family,
            anthropic_wire=scope.anthropic_wire,
            client_scope=scope.client_scope,
            text=text,
            signature=signature,
        )
        return PREFIX + self.encryptor.encrypt(envelope.model_dump_json()).decode("ascii")

    def open(self, token: str, *, client_scope: str, param: str) -> SealedThought:
        try:
            envelope = SealedThought.model_validate_json(self.encryptor.decrypt(token[len(PREFIX) :].encode("ascii")))
        except (InvalidToken, ValidationError, ValueError, UnicodeError) as exc:
            raise ClientPayloadError(
                "Invalid Antigravity reasoning state", param=param, code="invalid_provider_history"
            ) from exc
        if envelope.client_scope != client_scope:
            raise ClientPayloadError(
                "Antigravity reasoning state belongs to another client", param=param, code="invalid_provider_history"
            )
        return envelope


def is_sealed(item: JsonValue) -> bool:
    return (
        isinstance(item, dict) and isinstance(token := item.get("encrypted_content"), str) and token.startswith(PREFIX)
    )


def has_antigravity_replay(items: JsonValue) -> bool:
    return isinstance(items, list) and any(is_sealed(item) for item in items)


def omit_antigravity_replay(items: list[JsonValue]) -> list[JsonValue]:
    """Native OpenAI history: Gemini thoughts have no OpenAI representation, like Claude thinking."""
    return [item for item in items if not is_sealed(item)]
