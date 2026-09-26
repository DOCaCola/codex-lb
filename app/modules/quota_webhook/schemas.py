from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, SecretStr

from app.modules.shared.schemas import DashboardModel

ResetKind = Literal["scheduled", "unexpected"]


class Observation(BaseModel):
    used_percent: float = Field(ge=0, le=100, allow_inf_nan=False)
    reset_at: int | None
    window_minutes: int | None
    observed_at: datetime


class WebhookUpdate(DashboardModel):
    enabled: bool
    kinds: list[ResetKind] = Field(min_length=1, max_length=2)
    url: SecretStr | None = None
    signing_secret: SecretStr | None = None
    clear_url: bool = False
    clear_signing_secret: bool = False


class DeliveryStatus(DashboardModel):
    event_id: str
    status: str
    attempts: int
    created_at: datetime
    http_status: int | None
    error: str | None


class WebhookStatus(DashboardModel):
    enabled: bool = False
    kinds: list[ResetKind] = ["scheduled", "unexpected"]
    url_configured: bool = False
    signing_secret_configured: bool = False
    pending: int = 0
    last_delivery: DeliveryStatus | None = None


class QueuedTest(DashboardModel):
    event_id: str


class SavedDestination(DashboardModel):
    url: str | None = Field(repr=False)


def detect_reset(before: Observation, after: Observation) -> ResetKind | None:
    """Observation-based evidence, never an assertion of the provider's cause."""
    if after.observed_at <= before.observed_at or before.window_minutes != after.window_minutes:
        return None
    previous_deadline = before.reset_at
    if previous_deadline is None or previous_deadline <= 0 or after.used_percent >= 100:
        return None
    now = after.observed_at.timestamp()
    drop = before.used_percent - after.used_percent
    if before.observed_at.timestamp() <= previous_deadline <= now:
        if drop > 0 or (drop == 0 and after.reset_at is not None and after.reset_at > previous_deadline):
            return "scheduled"
        return None
    if now >= previous_deadline or drop < 5:
        return None
    if after.reset_at is not None:
        shift = after.reset_at - previous_deadline
        elapsed = (after.observed_at - before.observed_at).total_seconds()
        if 0 < shift <= elapsed * 2:
            return None
    return "unexpected"
