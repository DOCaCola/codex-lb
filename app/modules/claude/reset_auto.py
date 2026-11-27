"""Automatic redemption of reset grants before they expire, mirroring Codex reset credits."""

import logging
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid5

from app.core.config.background_jobs import background_job_enabled
from app.core.config.settings_cache import get_settings_cache
from app.db.models import ClaudeResetOperation
from app.db.session import get_background_session
from app.modules.claude.credentials import ClaudeError
from app.modules.claude.repository import ClaudeRepository
from app.modules.claude.reset_schemas import ConsumeGrant, Grant, GrantStatus
from app.modules.claude.resets import ClaudeResets
from app.modules.claude.schemas import AccountState

logger = logging.getLogger(__name__)

# Same window as Codex reset credits (reset_credits_refresh_scheduler._AUTO_REDEEM_WINDOW_SECONDS).
AUTO_REDEEM_WINDOW = timedelta(minutes=5)
_OPERATION_NAMESPACE = UUID("5d1f6c0e-6b7a-4c55-9a43-2f1d8c7e0b31")


def expiring_grant(status: GrantStatus, now: datetime) -> Grant | None:
    """The banked grant expiring soonest, once it expires within the automatic window."""
    expiring = [
        (grant.ends_at, grant)
        for grant in status.banked(now)
        if grant.ends_at is not None and grant.ends_at - now <= AUTO_REDEEM_WINDOW
    ]
    if not expiring:
        return None
    return min(expiring, key=lambda entry: entry[0])[1]


def automatic_operation_id(identity: str, grant: Grant) -> UUID:
    """One stable operation per account identity, grant and expiry, so every replica and tick shares it."""
    assert grant.ends_at is not None
    return uuid5(_OPERATION_NAMESPACE, f"{identity}:{grant.id}:{grant.ends_at.astimezone(UTC).isoformat()}")


async def auto_redeem_enabled() -> bool:
    """The Codex auto-redeem setting, which also stops with reset-credit polling."""
    if not await background_job_enabled("rate_limit_reset_credits_refresh_enabled"):
        return False
    return bool((await get_settings_cache().get()).auto_redeem_reset_credits_before_expiry)


async def redeem_expiring_grants(source_ids: Iterable[str]) -> None:
    for source_id in source_ids:
        async with get_background_session() as session:
            repository = ClaudeRepository(session)
            account = await repository.get(source_id)
            if (
                account is None
                or account.credential_status != "ready"
                or not account.source.is_enabled
                or account.identity_fingerprint is None
            ):
                continue
            usage = AccountState.model_validate_json(account.state_json).usage
            now = datetime.now(UTC)
            grant = expiring_grant(usage.cedar_ember, now) if usage is not None and usage.cedar_ember else None
            if grant is None:
                continue
            operation_id = automatic_operation_id(account.identity_fingerprint, grant)
            settled = await session.get(ClaudeResetOperation, str(operation_id))
            if settled is not None and settled.result_json is not None:
                continue
            try:
                result = await ClaudeResets(repository).consume(
                    source_id, ConsumeGrant(grant_id=grant.id, operation_id=operation_id, confirmed=True)
                )
            except ClaudeError as exc:
                logger.info(
                    "claude_reset_auto_redeem_skipped source_id=%s grant_id=%s reason=%s", source_id, grant.id, exc
                )
                continue
            answer = result.operation.result
            logger.info(
                "claude_reset_auto_redeem source_id=%s grant_id=%s result=%s",
                source_id,
                grant.id,
                answer.result if answer is not None else "unknown",
            )
