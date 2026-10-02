"""Same-account replay policy for refusals that prove no generation started.

Explicit overload refusals and pre-dispatch connection failures qualify; replay
safety is never inferred from ambiguous network errors.
"""

import math
import random
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

from starlette.requests import Request

from app.core.clock import Clock, Scheduler
from app.modules.model_sources.forwarding import ModelSourceForwardingError


def is_overload(error: ModelSourceForwardingError) -> bool:
    detail = error.payload.get("error")
    return error.upstream_status_code == 529 or (
        error.upstream_status_code == 503 and isinstance(detail, dict) and detail.get("type") == "overloaded_error"
    )


def retry_delay(error: ModelSourceForwardingError, *, now: datetime, available: float) -> float | None:
    delay = random.uniform(0.25, 0.5)
    hint = error.retry_after
    if hint:
        try:
            seconds = float(hint)
        except ValueError:
            try:
                seconds = (parsedate_to_datetime(hint).astimezone(UTC) - now).total_seconds()
            except (ValueError, TypeError, OverflowError):
                return None
        if not math.isfinite(seconds):
            return None
        delay = max(delay, seconds)
    return delay if delay < available else None


def connect_retry_delay(attempt: int, *, available: float) -> float | None:
    """Jittered backoff for the ``attempt``-th (zero-based) pre-dispatch retry, doubling per retry."""

    delay = random.uniform(0.25, 0.5) * 2**attempt
    return delay if delay < available else None


async def wait_for_retry(request: Request, delay: float, *, clock: Clock, scheduler: Scheduler) -> bool:
    deadline = clock.monotonic() + delay
    while True:
        if await request.is_disconnected():
            return False
        remaining = deadline - clock.monotonic()
        if remaining <= 0:
            return True
        await scheduler.sleep(min(remaining, 0.1))
