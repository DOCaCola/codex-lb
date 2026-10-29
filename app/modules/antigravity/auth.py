"""Access-token snapshots with proactive and reactive refresh.

Google refresh tokens do not rotate, so concurrent refreshes cannot invalidate each other and need no
durable claim. A reactive refresh after a 401 is skipped when another worker already replaced the
rejected access token. The native CLI never refreshes after a 401 (lab capture); that recovery is ours.
"""

from __future__ import annotations

import logging
import secrets
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from app.core.crypto import TokenEncryptor
from app.modules.antigravity import oauth
from app.modules.antigravity.errors import AntigravityError, TokenRejected
from app.modules.antigravity.repository import AntigravityRepository
from app.modules.antigravity.schemas import Credentials

logger = logging.getLogger(__name__)

REFRESH_MARGIN = timedelta(seconds=60)
REFRESH_BACKOFF = timedelta(minutes=1)


@dataclass(frozen=True)
class CredentialSnapshot:
    credentials: Credentials = field(repr=False)
    generation: int
    project_id: str | None

    @property
    def access_token(self) -> str:
        return self.credentials.access_token.get_secret_value()


class AntigravityAuth:
    def __init__(self, repository: AntigravityRepository, encryptor: TokenEncryptor) -> None:
        self.repository = repository
        self.encryptor = encryptor

    async def snapshot(self, source_id: str, *, rejected_token: str | None = None) -> CredentialSnapshot:
        row = await self.repository.get(source_id)
        if row is None:
            raise AntigravityError("Antigravity account not found", code="antigravity_account_missing")
        if row.credential_status != "ready":
            raise AntigravityError(
                "Antigravity credentials require reauthentication",
                code="antigravity_reauth_required",
                status_code=503,
            )
        credentials = oauth.decrypt_credentials(row.credentials_encrypted, self.encryptor)
        now = datetime.now(UTC)
        current = credentials.access_token.get_secret_value()
        if rejected_token is None and credentials.expires_at > now + REFRESH_MARGIN:
            return CredentialSnapshot(credentials, row.generation, row.project_id)
        if rejected_token is not None and not secrets.compare_digest(current, rejected_token):
            return CredentialSnapshot(credentials, row.generation, row.project_id)
        if row.retry_at is not None and row.retry_at.replace(tzinfo=UTC) > now:
            raise AntigravityError(
                "Antigravity token refresh is cooling down; retry later",
                code="antigravity_refresh_backoff",
                status_code=503,
            )
        generation = row.generation
        try:
            updated = await oauth.refresh(credentials.refresh_token.get_secret_value())
        except TokenRejected as exc:
            await self.repository.update_account(
                source_id,
                generation,
                **(
                    {"credential_status": "reauth_required"}
                    if exc.terminal
                    else {"retry_at": (now + REFRESH_BACKOFF).replace(tzinfo=None)}
                ),
            )
            await self.repository.session.commit()
            logger.warning("antigravity_token_refresh_rejected source_id=%s terminal=%s", source_id, exc.terminal)
            raise
        except AntigravityError:
            await self.repository.update_account(
                source_id, generation, retry_at=(now + REFRESH_BACKOFF).replace(tzinfo=None)
            )
            await self.repository.session.commit()
            raise
        if not await self.repository.update_account(
            source_id,
            generation,
            credentials_encrypted=oauth.encrypt_credentials(updated, self.encryptor),
            expires_at=updated.expires_at.replace(tzinfo=None),
            retry_at=None,
        ):
            raise AntigravityError("Antigravity credentials changed during refresh; retry the request", status_code=503)
        await self.repository.session.commit()
        return CredentialSnapshot(updated, generation, row.project_id)
