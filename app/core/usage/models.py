from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

LUNA_RESERVE_MODEL = "gpt-reserve"


class UsageWindow(BaseModel):
    model_config = ConfigDict(extra="ignore")

    used_percent: float | None = None
    reset_at: int | None = None
    limit_window_seconds: int | None = None
    reset_after_seconds: int | None = None


class RateLimitPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    allowed: bool | None = None
    primary_window: UsageWindow | None = None
    secondary_window: UsageWindow | None = None


class CreditsPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    has_credits: bool | None = None
    unlimited: bool | None = None
    balance: str | None = None


class RateLimitResetCreditsPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    available_count: int | None = None


class AdditionalRateLimitPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    limit_name: str
    metered_feature: str
    rate_limit: RateLimitPayload | None = None


class RateLimitUpsellPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    banner_type: str | None = None


class ReserveUsageSnapshot(BaseModel):
    observed_at: datetime
    ordinary_allowed: bool | None = None
    banner_type: str | None = None
    limit: AdditionalRateLimitPayload | None = None


class UsagePayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    plan_type: str | None = None
    account_id: str | None = None
    user_id: str | None = None
    workspace_id: str | None = None
    workspace_label: str | None = None
    seat_type: str | None = None
    rate_limit: RateLimitPayload | None = None
    credits: CreditsPayload | None = None
    rate_limit_reset_credits: RateLimitResetCreditsPayload | None = None
    additional_rate_limits: list[AdditionalRateLimitPayload] | None = None
    rate_limit_upsell: RateLimitUpsellPayload | None = None
