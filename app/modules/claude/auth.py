from __future__ import annotations

import asyncio
import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from app.core.crypto import TokenEncryptor
from app.core.utils.shared_future import wait_on_shared_future
from app.db.session import get_background_session
from app.modules.claude.client import ClaudeClient, TokenOutcomeUncertain, TokenRejected
from app.modules.claude.credentials import ClaudeError, decrypt_credentials, encrypt_credentials
from app.modules.claude.identity import bind_identity
from app.modules.claude.repository import ClaudeRepository
from app.modules.claude.schemas import Credentials


def grant_fingerprint(credentials: Credentials) -> str:
    return hashlib.sha256(credentials.refresh_token.get_secret_value().encode()).hexdigest()


@dataclass(frozen=True)
class CredentialSnapshot:
    credentials: Credentials = field(repr=False)
    generation: int


# In-flight refreshes by (source_id, generation). Each runs detached from the request that started it, in its own
# session: Anthropic rotates the refresh token, so a dispatched refresh must settle even when every waiting caller
# is cancelled (OmniRoute #20789; Codex AuthManager._run_refresh). Callers in this process share it.
_REFRESHES: dict[tuple[str, int], asyncio.Task[Credentials]] = {}


def _settled(key: tuple[str, int], task: asyncio.Task[Credentials]) -> None:
    if _REFRESHES.get(key) is task:
        del _REFRESHES[key]
    if not task.cancelled():
        # Its outcome is durable in the account row; waiters, if any, received it.
        task.exception()


class ClaudeAuth:
    def __init__(self, repository: ClaudeRepository, client: ClaudeClient, encryptor: TokenEncryptor) -> None:
        self.repository = repository
        self.client = client
        self.encryptor = encryptor

    async def credentials(self, source_id: str) -> Credentials:
        return (await self.snapshot(source_id)).credentials

    async def snapshot(self, source_id: str, *, rejected_generation: int | None = None) -> CredentialSnapshot:
        row = await self.repository.get(source_id)
        if row is None:
            raise ClaudeError("Claude account not found")
        if row.credential_status != "ready":
            raise ClaudeError("Claude credentials require reauthentication")
        now = datetime.now(UTC)
        generation = row.generation
        key = (source_id, generation)
        task = _REFRESHES.get(key)
        if task is None:
            if row.refresh_intent is not None:
                # Another worker owns this intent, or a crash left its outcome unknown. Never steal it, even
                # after a lease timeout: upstream might have rotated the token.
                raise ClaudeError("Claude refresh is in progress or its outcome is uncertain")
            credentials = decrypt_credentials(row.credentials_encrypted, self.encryptor)
            force = rejected_generation is not None and generation == rejected_generation
            if credentials.expires_at > now + timedelta(seconds=60) and not force:
                await bind_identity(self.client, self.repository, source_id, credentials)
                return CredentialSnapshot(credentials, generation)
            if row.retry_at is not None and row.retry_at > now.replace(tzinfo=None):
                raise ClaudeError("Claude refresh is cooling down; retry later")
            task = asyncio.create_task(self._refresh(source_id, generation, credentials))
            _REFRESHES[key] = task
            task.add_done_callback(lambda done: _settled(key, done))
        updated = await wait_on_shared_future(task)
        await bind_identity(self.client, self.repository, source_id, updated)
        return CredentialSnapshot(updated, generation + 1)

    async def _refresh(self, source_id: str, generation: int, credentials: Credentials) -> Credentials:
        """Claim, refresh and settle one generation; only a crash or shutdown leaves its intent behind, so no
        worker replays a refresh token upstream may already have consumed."""
        now = datetime.now(UTC)
        async with get_background_session() as session:
            repository = ClaudeRepository(session)
            intent = uuid.uuid4().hex
            if not await repository.claim_refresh(source_id, generation, intent, now.replace(tzinfo=None)):
                raise ClaudeError("Claude credentials changed or refresh is already in progress; retry later")
            try:
                updated = await self.client.refresh(credentials)
            except TokenRejected as exc:
                await repository.finish_refresh(
                    source_id,
                    generation,
                    intent,
                    status="reauth_required" if exc.terminal else "ready",
                    retry_at=None
                    if exc.terminal
                    else (now + timedelta(seconds=exc.retry_seconds)).replace(tzinfo=None),
                )
                raise
            except TokenOutcomeUncertain:
                await repository.finish_refresh(source_id, generation, intent, status="uncertain")
                raise
            if not await repository.finish_refresh(
                source_id,
                generation,
                intent,
                status="ready",
                encrypted=encrypt_credentials(updated, self.encryptor),
                expires_at=updated.expires_at.replace(tzinfo=None),
                fingerprint=grant_fingerprint(updated),
            ):
                raise ClaudeError("Claude credentials changed during refresh; retry with the current account")
        return updated
