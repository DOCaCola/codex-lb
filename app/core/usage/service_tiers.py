"""Billable service-tier resolution for Codex backend responses."""

from __future__ import annotations

# Relative cost of each canonical tier; a lower rank is always cheaper.
_COST_RANK = {"flex": 0, "default": 1, "auto": 1, "priority": 2, "ultrafast": 3}

# The ChatGPT Codex backend echoes ``default`` or ``auto`` as
# ``response.service_tier`` on turns it serves on the requested Fast tier, so
# these echoes cannot prove a downgrade (the same contract sub2api and
# opencodex apply to OAuth credentials).
_UNPROVEN_DOWNGRADE_ECHOES = frozenset({"default", "auto"})


def billable_service_tier(requested: str | None, observed: str | None) -> str | None:
    """Settle the billable tier between the forwarded and the echoed tier.

    The response tier may only lower the bill: a cheaper, known tier that is
    not an unproven echo replaces the requested one. A missing, unknown or
    more expensive echo leaves the requested tier in place. Without a
    requested tier, an echo of equal or lower cost is recorded as billable.
    """
    if observed is None:
        return requested
    observed_rank = _COST_RANK.get(observed)
    if observed_rank is None:
        return requested
    requested_rank = 1 if requested is None else _COST_RANK.get(requested, 1)
    if observed_rank > requested_rank:
        return requested
    if observed_rank < requested_rank and observed in _UNPROVEN_DOWNGRADE_ECHOES:
        return requested
    return observed
