"""Generation-fenced quota evidence from physical response headers."""

import logging
import math
from collections.abc import Mapping
from datetime import UTC, datetime

from app.core.utils.shared_future import _await_cleanup_deferring_cancellation
from app.db.session import get_background_session
from app.modules.claude.repository import ClaudeRepository
from app.modules.claude.schemas import (
    AccountState,
    HeaderOverageObservation,
    HeaderQuotaObservation,
    HeaderWindow,
    QuotaWindow,
    UsageSnapshot,
)

logger = logging.getLogger(__name__)

_HEADER_PREFIXES: tuple[tuple[HeaderWindow, str], ...] = (
    ("five_hour", "5h"),
    ("seven_day", "7d"),
    ("seven_day_overage_included", "7d_oi"),
)


def parse_headers(
    headers: Mapping[str, str], *, requested_at: datetime, observed_at: datetime
) -> dict[HeaderWindow, HeaderQuotaObservation]:
    normalized = {key.lower(): value for key, value in headers.items()}
    observations: dict[HeaderWindow, HeaderQuotaObservation] = {}
    for name, prefix in _HEADER_PREFIXES:
        raw = normalized.get(f"anthropic-ratelimit-unified-{prefix}-utilization")
        if raw is None or not raw.strip():
            continue
        try:
            fraction = float(raw)
        except ValueError:
            continue
        percent = fraction * 100
        if fraction < 0 or not math.isfinite(percent):
            continue
        reset = None
        raw_reset = normalized.get(f"anthropic-ratelimit-unified-{prefix}-reset")
        if raw_reset:
            try:
                seconds = float(raw_reset)
                if math.isfinite(seconds) and seconds > 0:
                    reset = datetime.fromtimestamp(seconds, UTC)
            except (ValueError, OverflowError, OSError):
                pass
        observations[name] = HeaderQuotaObservation(
            window=QuotaWindow(utilization=round(percent, 6), resets_at=reset),
            requested_at=requested_at,
            observed_at=observed_at,
        )
    return observations


def parse_overage(headers: Mapping[str, str], *, requested_at: datetime) -> HeaderOverageObservation | None:
    raw = {key.lower(): value for key, value in headers.items()}.get("anthropic-ratelimit-unified-overage-in-use")
    value = raw.strip().lower() if raw is not None else None
    if value not in {"true", "false"}:
        return None
    return HeaderOverageObservation(in_use=value == "true", requested_at=requested_at)


async def record_headers(
    source_id: str, generation: int, headers: Mapping[str, str], *, requested_at: datetime
) -> None:
    evidence = parse_headers(headers, requested_at=requested_at, observed_at=datetime.now(UTC))
    overage = parse_overage(headers, requested_at=requested_at)
    if not evidence and overage is None:
        return
    try:
        # Inline and run to completion, like the other request-path bookkeeping:
        # cancelling a commit mid-flight wedges the connection instead of
        # freeing the response. Caller cancellation is surfaced afterwards.
        cancellation = await _await_cleanup_deferring_cancellation(_persist(source_id, generation, evidence, overage))
    except Exception:
        # No credentials, header values, SQL, or exception bodies in diagnostics.
        logger.warning("claude_quota_observation_failed source_id=%s", source_id)
        return
    if cancellation is not None:
        raise cancellation


async def _persist(
    source_id: str,
    generation: int,
    evidence: dict[HeaderWindow, HeaderQuotaObservation],
    overage: HeaderOverageObservation | None,
) -> None:
    def merge(current: AccountState) -> AccountState | None:
        updates = {
            name: observation
            for name, observation in evidence.items()
            if (name not in current.reset_barriers or observation.requested_at > current.reset_barriers[name])
            and (name not in current.header_usage or observation.requested_at > current.header_usage[name].requested_at)
        }
        newer_overage = overage is not None and (
            current.header_overage is None or overage.requested_at > current.header_overage.requested_at
        )
        if not updates and not newer_overage:
            return None
        return current.model_copy(
            update={
                "header_usage": {**current.header_usage, **updates},
                "header_overage": overage if newer_overage else current.header_overage,
            }
        )

    async with get_background_session() as session:
        repository = ClaudeRepository(session)
        merged = await repository.mutate_state(source_id, generation, merge)
        if merged is None:
            return
        from app.modules.claude.quota import quota_status

        now = datetime.now(UTC)
        windows = quota_status(merged, now=now).windows
        usage = UsageSnapshot.model_validate(
            {
                window.name: {"utilization": window.utilization, "resets_at": window.resets_at}
                for window in windows
                if window.name in evidence and window.provenance == "inference_header" and window.freshness == "fresh"
            }
        )
        await repository.record_quota(source_id, usage, now, provenance="inference_header", sample_seconds=60)
        await session.commit()
