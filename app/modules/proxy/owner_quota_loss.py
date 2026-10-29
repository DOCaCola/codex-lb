"""Quota-caused loss of the account that holds a previous response.

A ``previous_response_id`` continuation can only run on the account that
stored the response. When that account is unavailable because its upstream
usage window is spent, the continuation cannot run until the reset, which may
be days away; resending the full conversation without the anchor runs it on
any other account. Other owner losses (authentication, operator pause, local
capacity) keep the generic owner-unavailable contract.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from app.db.models import AccountStatus
from app.modules.proxy.repo_bundle import ProxyRepoFactory

logger = logging.getLogger(__name__)

# Persisted statuses that prove the owner is unselectable because of its
# upstream usage state rather than authentication, deactivation, or a pause.
# ``REAUTH_REQUIRED`` stays selectable and therefore never causes owner loss.
OWNER_QUOTA_UNAVAILABLE_STATUSES = frozenset({AccountStatus.RATE_LIMITED, AccountStatus.QUOTA_EXCEEDED})


@dataclass(frozen=True, slots=True)
class OwnerQuotaLoss:
    resets_at: int | None


async def load_owner_quota_loss(repo_factory: ProxyRepoFactory, account_id: str) -> OwnerQuotaLoss | None:
    """Return the owner's quota loss, or ``None`` when its loss has another cause.

    A failed lookup proves nothing, so the request keeps the owner-bound
    contract.
    """
    try:
        async with repo_factory() as repos:
            account = await repos.accounts.get_by_id_fresh(account_id)
            # Read inside the repository scope: the session expires ORM
            # attributes when it closes.
            if account is None or account.status not in OWNER_QUOTA_UNAVAILABLE_STATUSES:
                return None
            return OwnerQuotaLoss(resets_at=account.reset_at)
    except Exception:
        logger.warning(
            "Previous-response owner status lookup failed; keeping the request owner-bound",
            exc_info=True,
        )
        return None


def owner_quota_loss_message(loss: OwnerQuotaLoss) -> str:
    if loss.resets_at is None:
        return "Previous response owner account reached its usage limit; retry without previous_response_id."
    resets = datetime.fromtimestamp(loss.resets_at, UTC).strftime("%Y-%m-%d %H:%M UTC")
    return (
        f"Previous response owner account reached its usage limit (resets {resets}); "
        "retry without previous_response_id."
    )
