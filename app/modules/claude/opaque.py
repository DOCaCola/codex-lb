"""Authenticated, account/model/client-bound Claude signed-thinking envelopes."""

from __future__ import annotations

from dataclasses import dataclass

from cryptography.fernet import InvalidToken
from pydantic import BaseModel, JsonValue, ValidationError

from app.core.crypto import TokenEncryptor
from app.core.openai.exceptions import ClientPayloadError

PREFIX = "claude-v1."


class SignedBlock(BaseModel):
    source_id: str
    model: str
    client_scope: str
    conversation_id: str
    block: dict[str, JsonValue]


@dataclass(frozen=True)
class OpaqueScope:
    source_id: str
    model: str
    client_scope: str
    conversation_id: str


class ClaudeOpaqueState:
    def __init__(self, encryptor: TokenEncryptor) -> None:
        self.encryptor = encryptor

    def encode(self, scope: OpaqueScope, block: dict[str, JsonValue]) -> str:
        if block.get("type") not in ("thinking", "redacted_thinking"):
            raise ValueError("Only native Claude thinking blocks belong in opaque reasoning")
        envelope = SignedBlock(
            source_id=scope.source_id,
            model=scope.model,
            client_scope=scope.client_scope,
            conversation_id=scope.conversation_id,
            block=block,
        )
        return PREFIX + self.encryptor.encrypt(envelope.model_dump_json()).decode("ascii")

    def decode(self, token: str, *, model: str, client_scope: str, conversation_id: str) -> SignedBlock:
        if not token.startswith(PREFIX):
            raise ClientPayloadError("Reasoning belongs to another provider; resend portable context", param="input")
        try:
            envelope = SignedBlock.model_validate_json(self.encryptor.decrypt(token[len(PREFIX) :].encode("ascii")))
        except (InvalidToken, ValidationError, ValueError, UnicodeError) as exc:
            raise ClientPayloadError("Invalid Claude reasoning state", param="input") from exc
        if (envelope.model, envelope.client_scope, envelope.conversation_id) != (model, client_scope, conversation_id):
            raise ClientPayloadError("Claude reasoning state belongs to another model or conversation", param="input")
        if envelope.block.get("type") not in ("thinking", "redacted_thinking"):
            raise ClientPayloadError("Invalid Claude reasoning block", param="input")
        return envelope
