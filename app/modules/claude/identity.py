"""Authenticated provider identity, independent of rotating tokens and names."""

import hashlib
import json

from sqlalchemy import update
from sqlalchemy.exc import IntegrityError

from app.db.models import ClaudeAccount
from app.db.session import get_background_session
from app.modules.claude.client import ClaudeClient
from app.modules.claude.credentials import ClaudeError
from app.modules.claude.repository import ClaudeRepository
from app.modules.claude.schemas import AccountState, AuthenticatedProfile, Credentials, PendingReconnectView
from app.modules.claude.version import ClaudeVersionService
from app.modules.model_sources.forwarding import ModelSourceForwardingError


class ClaudeIdentityChanged(ClaudeError):
    """Explicit replacement raced a request; a retry prepares the current identity."""

    code = "claude_identity_changed"
    status_code = 503

    def __init__(self) -> None:
        super().__init__("Claude credentials were replaced during this request; retry it.")

    @property
    def response_headers(self) -> dict[str, str]:
        return {"Retry-After": "1"}


async def require_current_identity(source_id: str, identity_generation: int) -> None:
    """Prepared requests cannot start a new attempt after their identity was replaced."""
    async with get_background_session() as session:
        account = await session.get(ClaudeAccount, source_id)
        if (
            account is None
            or AccountState.model_validate_json(account.state_json).identity_generation != identity_generation
        ):
            error = ClaudeIdentityChanged()
            raise ModelSourceForwardingError(
                status_code=error.status_code,
                payload={"error": {"type": error.error_type, "code": error.code, "message": str(error)}},
                retry_after="1",
            )


class ReconnectIdentityMismatch(ClaudeError):
    """A verified fingerprint mismatch, classified using the saved account UUID and held for confirmation."""

    def __init__(
        self, saved_account_uuid: str | None, incoming_account_uuid: str, pending: PendingReconnectView
    ) -> None:
        self.pending = pending
        if saved_account_uuid is None:
            self.code = "claude_reconnect_identity_unverified"
            message = (
                "This sign-in differs from the saved identity, which cannot be compared in detail, so an "
                "account change cannot be distinguished from an organization change. Existing credentials "
                "were not replaced. Confirm to replace the saved identity with this sign-in."
            )
        elif saved_account_uuid != incoming_account_uuid:
            self.code = "claude_reconnect_account_mismatch"
            message = (
                "This sign-in authenticated a different Claude account. Existing credentials were not replaced. "
                "Confirm to replace the saved identity, or sign in with the original account or add this "
                "account separately."
            )
        else:
            self.code = "claude_reconnect_organization_changed"
            message = (
                "This sign-in authenticated the same Claude account, but a different organization. "
                "Existing credentials were not replaced. Confirm to use this organization for this entry; "
                "resources owned by the previous organization stay unavailable."
            )
        super().__init__(message)


async def authenticated_profile(
    client: ClaudeClient, repository: ClaudeRepository, credentials: Credentials
) -> AuthenticatedProfile:
    version = await ClaudeVersionService(repository.session).snapshot()
    return await client.profile(credentials.access_token.get_secret_value(), version.version)


def profile_identity(profile: AuthenticatedProfile) -> str:
    return hashlib.sha256(json.dumps([profile.account.uuid, profile.organization.uuid]).encode()).hexdigest()


async def bind_identity(
    client: ClaudeClient, repository: ClaudeRepository, source_id: str, credentials: Credentials
) -> None:
    row = await repository.get(source_id)
    if row is None:
        raise ClaudeError("Claude account was removed")
    if row.identity_fingerprint is not None and row.provider_account_uuid is not None:
        return
    generation = row.generation
    profile = await authenticated_profile(client, repository, credentials)
    fingerprint = profile_identity(profile)
    if row.identity_fingerprint is not None and row.identity_fingerprint != fingerprint:
        raise ClaudeError("Claude credentials authenticate a different account and organization")
    account_uuid = profile.account.uuid
    try:
        changed = await repository.session.scalar(
            update(ClaudeAccount)
            .where(
                ClaudeAccount.source_id == source_id,
                ClaudeAccount.generation == generation,
                ClaudeAccount.identity_fingerprint.is_(None) | (ClaudeAccount.identity_fingerprint == fingerprint),
            )
            .values(
                identity_fingerprint=fingerprint,
                provider_account_uuid=account_uuid,
                account_email=profile.account.email,
                organization_name=profile.organization.name,
                version=ClaudeAccount.version + 1,
            )
            .returning(ClaudeAccount.source_id)
            .execution_options(synchronize_session=False)
        )
        await repository.session.commit()
    except IntegrityError as exc:
        await repository.session.rollback()
        raise ClaudeError("This authenticated Claude account and organization are already enrolled") from exc
    if changed is None:
        current = await repository.get(source_id)
        if (
            current is None
            or current.generation != generation
            or current.identity_fingerprint != fingerprint
            or current.provider_account_uuid != account_uuid
        ):
            raise ClaudeError("Claude credentials changed during identity verification; retry")
