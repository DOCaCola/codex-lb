"""Safe explanations from actual selection exclusions, never account identities."""

from collections import Counter
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Literal

RoutingExclusion = Literal[
    "paused",
    "deactivated",
    "credentials",
    "refreshing",
    "refresh_backoff",
    "model",
    "reasoning",
    "quota",
    "cooldown",
    "error_backoff",
    "excluded",
    "authentication",
    "balance",
    "rate_limit",
]


def explain_unavailable(message: str, reasons: Iterable[RoutingExclusion], *, retry_at: float | None = None) -> str:
    counts = Counter(reasons)
    if not counts:
        return message
    summary = ", ".join(f"{reason}: {counts[reason]}" for reason in sorted(counts))
    recovery = ""
    if retry_at is not None:
        recovery = f"; known recovery: {datetime.fromtimestamp(retry_at, UTC).isoformat()}"
    return f"{message.rstrip('.')}. Routing exclusions ({summary}{recovery})."
