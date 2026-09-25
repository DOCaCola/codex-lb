from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime, timedelta

from app.core.crypto import TokenEncryptor
from app.modules.claude.client import ClaudeClient, TokenOutcomeUncertain, TokenRejected
from app.modules.claude.credentials import ClaudeError, decrypt_credentials, encrypt_credentials
from app.modules.claude.identity import bind_identity
from app.modules.claude.repository import ClaudeRepository
from app.modules.claude.schemas import Credentials


def grant_fingerprint(credentials: Credentials) -> str:
    return hashlib.sha256(credentials.refresh_token.get_secret_value().encode()).hexdigest()


class ClaudeAuth:
    def __init__(self, repository: ClaudeRepository, client: ClaudeClient, encryptor: TokenEncryptor) -> None:
        self.repository = repository
        self.client = client
        self.encryptor = encryptor

    async def credentials(self, source_id: str) -> Credentials:
        row = await self.repository.get(source_id)
        if row is None:
            raise ClaudeError("Claude account not found")
        if row.credential_status != "ready":
            raise ClaudeError("Claude credentials require reauthentication")
        now = datetime.now(UTC)
        if row.refresh_intent is not None:
            # A live worker may still own this intent. Never steal it, even
            # after a lease timeout: upstream might have rotated the token.
            raise ClaudeError("Claude refresh is in progress or its outcome is uncertain")
        credentials = decrypt_credentials(row.credentials_encrypted, self.encryptor)
        if credentials.expires_at > now + timedelta(seconds=60):
            await bind_identity(self.client, self.repository, source_id, credentials)
            return credentials
        if row.retry_at is not None and row.retry_at > now.replace(tzinfo=None):
            raise ClaudeError("Claude refresh is cooling down; retry later")
        generation = row.generation
        intent = uuid.uuid4().hex
        if not await self.repository.claim_refresh(source_id, generation, intent, now.replace(tzinfo=None)):
            raise ClaudeError("Claude credentials changed or refresh is already in progress; retry later")
        try:
            updated = await self.client.refresh(credentials)
        except TokenRejected as exc:
            await self.repository.finish_refresh(
                source_id,
                generation,
                intent,
                status="reauth_required" if exc.terminal else "ready",
                retry_at=None if exc.terminal else (now + timedelta(seconds=exc.retry_seconds)).replace(tzinfo=None),
            )
            raise
        except TokenOutcomeUncertain:
            await self.repository.finish_refresh(source_id, generation, intent, status="uncertain")
            raise
        # Cancellation/crash retains durable intent; it cannot cause a second
        # worker to replay the consumed refresh token after restart.
        if not await self.repository.finish_refresh(
            source_id,
            generation,
            intent,
            status="ready",
            encrypted=encrypt_credentials(updated, self.encryptor),
            expires_at=updated.expires_at.replace(tzinfo=None),
            fingerprint=grant_fingerprint(updated),
        ):
            raise ClaudeError("Claude credentials changed during refresh; retry with the current account")
        await bind_identity(self.client, self.repository, source_id, updated)
        return updated
