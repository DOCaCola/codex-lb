"""Durable account consequences of classified upstream failures, shared by metadata and inference."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from app.modules.antigravity.classify import UpstreamFailure
from app.modules.antigravity.repository import AntigravityRepository
from app.modules.antigravity.schemas import AccountState, QuotaFamily, VerificationNotice

logger = logging.getLogger(__name__)

# OmniRoute measured VALIDATION_REQUIRED as transient on healthy accounts: cool down, don't disable.
VERIFICATION_COOLDOWN = timedelta(minutes=15)
# Quota exhaustion without a reported reset waits for the next quota reading.
QUOTA_FALLBACK_COOLDOWN = timedelta(minutes=30)
# Rate limits at or above this delay move the conversation; shorter ones are waited out in place.
MOVE_THRESHOLD = timedelta(seconds=3)
MODEL_UNAVAILABLE_COOLDOWN = timedelta(hours=1)

ACCOUNT_SCOPE = "account"


def family_scope(family: QuotaFamily) -> str:
    return f"family:{family}"


def model_scope(family_id: str) -> str:
    return f"model:{family_id}"


async def record_failure(
    repository: AntigravityRepository,
    source_id: str,
    generation: int,
    failure: UpstreamFailure,
    *,
    quota_family: QuotaFamily | None = None,
    model_family: str | None = None,
    now: datetime | None = None,
) -> None:
    """Persist what this failure proves about the account; the caller owns the commit."""
    now = now or datetime.now(UTC)
    naive = now.replace(tzinfo=None)
    match failure.kind:
        case "banned":
            await repository.update_account(
                source_id, generation, hold="banned", hold_reason=failure.message, hold_at=naive
            )
            logger.warning("antigravity_account_banned source_id=%s", source_id)
        case "location":
            await repository.update_account(
                source_id, generation, hold="location_unsupported", hold_reason=failure.message, hold_at=naive
            )
            logger.warning("antigravity_location_unsupported source_id=%s", source_id)
        case "verification":
            await repository.cool_down(source_id, ACCOUNT_SCOPE, now + VERIFICATION_COOLDOWN, "verification_required")

            def notice(state: AccountState) -> AccountState:
                state.verification = VerificationNotice(url=failure.verification_url, observed_at=now)
                return state

            await repository.mutate_state(source_id, generation, notice)
            logger.warning("antigravity_verification_required source_id=%s", source_id)
        case "quota" if quota_family is not None:
            until = failure.reset_at or now + QUOTA_FALLBACK_COOLDOWN
            await repository.cool_down(source_id, family_scope(quota_family), until, "quota_exhausted")
        case "rate_limit" if model_family is not None and failure.retry_after is not None:
            if failure.retry_after >= MOVE_THRESHOLD:
                await repository.cool_down(
                    source_id, model_scope(model_family), now + failure.retry_after, "rate_limited"
                )
        case "not_found" if model_family is not None:
            await repository.cool_down(
                source_id, model_scope(model_family), now + MODEL_UNAVAILABLE_COOLDOWN, "model_unavailable"
            )
        case _:
            return
