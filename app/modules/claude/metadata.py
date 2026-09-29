"""Metadata polling policy, independent of inference/authentication backoff."""

from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime

from app.modules.claude.credentials import ClaudeError
from app.modules.claude.schemas import AccountState, MetadataEndpoint

USAGE_INTERVAL = timedelta(minutes=3)
CATALOG_INTERVAL = timedelta(hours=6)
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
    return now + USAGE_INTERVAL


class MetadataHTTPError(ClaudeError):
    def __init__(self, endpoint: str, status: int, retry_after: str | None) -> None:
        self.status = status
        self.retry_at = retry_deadline(retry_after, datetime.now(UTC))
        super().__init__(
            f"Claude {endpoint} returned HTTP {status}; next metadata attempt after {self.retry_at.isoformat()}"
        )


def refresh_due(state: AccountState, endpoint: MetadataEndpoint, now: datetime, *, force: bool) -> bool:
    refresh = state.metadata_refresh.get(endpoint)
    if refresh is not None:
        if refresh.lease_until is not None and refresh.lease_until > now:
            return False
        if refresh.retry_at is not None:
            return refresh.retry_at <= now
    updated = state.catalog_updated_at if endpoint == "catalog" else state.usage_updated_at
    interval = CATALOG_INTERVAL if endpoint == "catalog" else USAGE_INTERVAL
    return force or updated is None or now - updated >= interval
