"""Authenticated, client-bound Claude reasoning and search state with account/model provenance."""

from __future__ import annotations

from dataclasses import dataclass

from cryptography.fernet import InvalidToken
from pydantic import BaseModel, JsonValue, ValidationError

from app.core.crypto import TokenEncryptor
from app.core.openai.exceptions import ClientPayloadError
from app.core.openai.reasoning import CLAUDE_REASONING_PREFIX

PREFIX = CLAUDE_REASONING_PREFIX


class SignedBlock(BaseModel):
    source_id: str
    model: str
    client_scope: str
    block: dict[str, JsonValue]
    # A progress update whose text was also delivered as a visible commentary message.
    presented: bool = False
    identity_generation: int = 1


@dataclass(frozen=True)
class OpaqueScope:
    source_id: str
    model: str
    client_scope: str
    identity_generation: int = 1


class ClaudeOpaqueState:
    def __init__(self, encryptor: TokenEncryptor) -> None:
        self.encryptor = encryptor

    def encode(self, scope: OpaqueScope, block: dict[str, JsonValue], *, presented: bool = False) -> str:
        if block.get("type") not in ("thinking", "redacted_thinking", "web_search"):
            raise ValueError("Only native Claude thinking or search state belongs in opaque reasoning")
        envelope = SignedBlock(
            source_id=scope.source_id,
            model=scope.model,
            client_scope=scope.client_scope,
            block=block,
            presented=presented,
            identity_generation=scope.identity_generation,
        )
        return PREFIX + self.encryptor.encrypt(envelope.model_dump_json()).decode("ascii")

    def authenticate(self, token: str, *, client_scope: str) -> SignedBlock:
        if not token.startswith(PREFIX):
            raise ClientPayloadError(
                "Reasoning belongs to another provider; resend portable context",
                param="input",
                code="nonportable_provider_history",
            )
        try:
            envelope = SignedBlock.model_validate_json(self.encryptor.decrypt(token[len(PREFIX) :].encode("ascii")))
        except (InvalidToken, ValidationError, ValueError, UnicodeError) as exc:
            raise ClientPayloadError(
                "Invalid Claude reasoning state", param="input", code="invalid_provider_history"
            ) from exc
        if envelope.client_scope != client_scope:
            raise ClientPayloadError(
                "Claude reasoning state belongs to another client", param="input", code="invalid_provider_history"
            )
        if envelope.block.get("type") not in ("thinking", "redacted_thinking", "web_search"):
            raise ClientPayloadError("Invalid Claude reasoning block", param="input", code="invalid_provider_history")
        return envelope
