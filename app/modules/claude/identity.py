"""Authenticated provider identity, independent of rotating tokens and names."""

import hashlib
import json

from sqlalchemy import update
from sqlalchemy.exc import IntegrityError

from app.db.models import ClaudeAccount
from app.modules.claude.client import ClaudeClient
from app.modules.claude.credentials import ClaudeError
from app.modules.claude.repository import ClaudeRepository
from app.modules.claude.schemas import AuthenticatedProfile, Credentials
from app.modules.claude.version import ClaudeVersionService


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
