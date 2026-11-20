"""Metadata polling policy, independent of inference/authentication backoff."""

from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime

from app.modules.claude.credentials import ClaudeError
from app.modules.claude.schemas import AccountState, MetadataEndpoint

# Reply headers are the primary quota source (as in Claude Code, which never polls usage).
# The endpoint fills idle accounts, refreshes data only it reports, and confirms a window
# once its known reset passed: an exhausted account receives no replies to report it.
USAGE_IDLE_INTERVAL = timedelta(minutes=15)
USAGE_SNAPSHOT_INTERVAL = timedelta(hours=1)
# Claude Code's wait after a refusal without Retry-After.
RETRY_DEFAULT = timedelta(minutes=5)
CATALOG_INTERVAL = timedelta(hours=6)
SUBSCRIPTION_INTERVAL = timedelta(hours=6)
FETCH_TIMEOUT_SECONDS = 60
CLAIM_LEASE = timedelta(seconds=90)


def retry_deadline(value: str | None, now: datetime) -> datetime:
    if value is not None:
        value = value.strip()
        try:
            if value.isascii() and value.isdecimal():
                return now + timedelta(seconds=int(value))
            deadline = parsedate_to_datetime(value)
            if deadline.tzinfo is not None:
                return max(now, deadline.astimezone(UTC))
        except (ValueError, TypeError, OverflowError):
            pass
    return now + RETRY_DEFAULT


class MetadataHTTPError(ClaudeError):
    def __init__(self, endpoint: str, status: int, retry_after: str | None) -> None:
        self.status = status
        self.retry_at = retry_deadline(retry_after, datetime.now(UTC))
        super().__init__(
            f"Claude {endpoint} returned HTTP {status}; next metadata attempt after {self.retry_at.isoformat()}"
        )


def metadata_updated_at(state: AccountState, endpoint: MetadataEndpoint) -> datetime | None:
    match endpoint:
        case "catalog":
            return state.catalog_updated_at
        case "usage":
            return state.usage_updated_at
        case "subscription":
            return state.subscription_updated_at


def _usage_due(state: AccountState, now: datetime) -> bool:
    polled = state.usage_updated_at
    if polled is None or now - polled >= USAGE_SNAPSHOT_INTERVAL:
        return True
    headers = [state.header_usage.get("five_hour"), state.header_usage.get("seven_day")]
    newest = max([polled, *(observation.observed_at for observation in headers if observation is not None)])
    return now - newest >= USAGE_IDLE_INTERVAL or _reset_passed_since_reading(state, polled, now)


def _reset_passed_since_reading(state: AccountState, polled: datetime, now: datetime) -> bool:
    """Whether a window's known reset passed after its latest reading."""
    usage = state.usage
    polled_windows = (
        (
            usage.five_hour,
            usage.seven_day,
            usage.seven_day_opus,
            usage.seven_day_sonnet,
            usage.seven_day_overage_included,
        )
        if usage is not None
        else ()
    )
    deadlines = [(window.resets_at, polled) for window in polled_windows if window is not None]
    deadlines += [
        (observation.window.resets_at, max(observation.observed_at, polled))
        for observation in state.header_usage.values()
    ]
    return any(reset is not None and read_at < reset <= now for reset, read_at in deadlines)


def refresh_due(
    state: AccountState, endpoint: MetadataEndpoint, now: datetime, *, force: bool, generation: int
) -> bool:
    refresh = state.metadata_refresh.get(endpoint)
    if refresh is not None:
        if refresh.lease_until is not None and refresh.lease_until > now:
            return False
        # A forced check skips the backoff after our own failures, never a provider rate limit
        # of the current credential. A refreshed token follows the normal cadence.
        binding = refresh.rate_limited_generation == generation or (
            refresh.rate_limited_generation is None and not force
        )
        if refresh.retry_at is not None and binding:
            return refresh.retry_at <= now
    if force:
        return True
    if endpoint == "usage":
        return _usage_due(state, now)
    updated = metadata_updated_at(state, endpoint)
    interval = CATALOG_INTERVAL if endpoint == "catalog" else SUBSCRIPTION_INTERVAL
    return updated is None or now - updated >= interval
