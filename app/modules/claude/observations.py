"""Best-effort, generation-fenced quota evidence from physical response headers."""

import logging
import math
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Literal

import anyio

from app.db.session import get_background_session
from app.modules.claude.repository import ClaudeRepository
from app.modules.claude.schemas import AccountState, HeaderQuotaObservation, QuotaWindow, UsageSnapshot

logger = logging.getLogger(__name__)


def parse_headers(
    headers: Mapping[str, str], *, requested_at: datetime, observed_at: datetime
) -> dict[Literal["five_hour", "seven_day"], HeaderQuotaObservation]:
    normalized = {key.lower(): value for key, value in headers.items()}
    observations: dict[Literal["five_hour", "seven_day"], HeaderQuotaObservation] = {}
    for name, prefix in (("five_hour", "5h"), ("seven_day", "7d")):
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


async def record_headers(
    source_id: str, generation: int, headers: Mapping[str, str], *, requested_at: datetime
) -> None:
    evidence = parse_headers(headers, requested_at=requested_at, observed_at=datetime.now(UTC))
    if not evidence:
        return

    def merge(current: AccountState) -> AccountState | None:
        updates = {
            name: observation
            for name, observation in evidence.items()
            if (name not in current.reset_barriers or observation.requested_at > current.reset_barriers[name])
            and (name not in current.header_usage or observation.requested_at > current.header_usage[name].requested_at)
        }
        if not updates:
            return None
        return current.model_copy(update={"header_usage": {**current.header_usage, **updates}})

    try:
        # No detached tasks; database stalls cannot hold an accepted response indefinitely.
        with anyio.fail_after(0.5):
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
                        if window.name in evidence
                        and window.provenance == "inference_header"
                        and window.freshness == "fresh"
                    }
                )
                await repository.record_quota(source_id, usage, now, provenance="inference_header", sample_seconds=60)
                await session.commit()
    except Exception:
        # No credentials, header values, SQL, or exception bodies in diagnostics.
        logger.warning("claude_quota_observation_failed source_id=%s", source_id)
