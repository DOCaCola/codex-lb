"""Same-account replay policy for failures that prove no generation started.

Transient upstream refusals and pre-dispatch connection failures qualify; replay
safety is never inferred from timeouts or connections that broke after dispatch.
"""

import math
import random
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

from starlette.requests import Request

from app.core.clock import Clock, Scheduler
from app.modules.model_sources.forwarding import ModelSourceForwardingError

# Claude Code's own retryable statuses besides 5xx; 429 and 401 have their own recovery.
_TRANSIENT_STATUSES = frozenset({408, 409})


def upstream_header(error: ModelSourceForwardingError, name: str) -> str | None:
    return next((value for key, value in error.upstream_headers.items() if key.lower() == name), None)


def is_transient_refusal(error: ModelSourceForwardingError) -> bool:
    """A refusal Claude Code retries: 408, 409 or any 5xx status, unless Anthropic sends ``x-should-retry: false``."""
    status = error.upstream_status_code
    if status is None or not (status in _TRANSIENT_STATUSES or status >= 500):
        return False
    return (upstream_header(error, "x-should-retry") or "").strip().lower() != "false"


def retry_delay(error: ModelSourceForwardingError, attempt: int, *, now: datetime, available: float) -> float | None:
    """Jittered wait before the ``attempt``-th (zero-based) retry, doubling per retry; Retry-After is a minimum."""

    delay = random.uniform(0.25, 0.5) * 2**attempt
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


async def wait_for_retry(request: Request, delay: float, *, clock: Clock, scheduler: Scheduler) -> bool:
    deadline = clock.monotonic() + delay
    while True:
        if await request.is_disconnected():
            return False
        remaining = deadline - clock.monotonic()
        if remaining <= 0:
            return True
        await scheduler.sleep(min(remaining, 0.1))
