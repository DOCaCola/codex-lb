"""Wire and dashboard contracts for manual cedar_ember redemption."""

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from app.modules.shared.schemas import DashboardModel

ResetWindow = Literal["five_hour", "seven_day", "seven_day_overage_included"]
GrantId = Annotated[str, Field(pattern=r"^[a-z0-9_-]{1,40}$")]
Count = Annotated[int, Field(strict=True, ge=0)]


class Grant(BaseModel):
    model_config = ConfigDict(hide_input_in_errors=True)
    id: GrantId
    label: str = Field(max_length=500)
    resets_total: Count
    resets_left: Count
    starts_at: AwareDatetime | None = None
    ends_at: AwareDatetime | None = None
    clears: list[ResetWindow]
    paused: bool = Field(strict=True)
    usable_now: bool = Field(strict=True)
    use_requires_limit: bool = Field(strict=True)

    @model_validator(mode="after")
    def valid_counts(self) -> "Grant":
        if self.resets_left > self.resets_total:
            raise ValueError("Invalid reset grant count")
        return self


class GrantStatus(BaseModel):
    eligible: bool = Field(strict=True)
    ineligible_reason: str | None = Field(default=None, max_length=128)
    at_limit: bool = Field(strict=True)
    grants: list[Grant]
    cooldown_until: AwareDatetime | None = None

    @model_validator(mode="after")
    def unique_grants(self) -> "GrantStatus":
        if len({g.id for g in self.grants}) != len(self.grants):
            raise ValueError("Duplicate reset grants")
        return self

    def usable(self, grant_id: str, now: datetime) -> bool:
        return (
            self.eligible
            and (self.cooldown_until is None or self.cooldown_until <= now)
            and any(
                g.id == grant_id
                and g.usable_now
                and not g.paused
                and g.resets_left > 0
                and (not g.use_requires_limit or self.at_limit)
                and (g.starts_at is None or g.starts_at <= now)
                and (g.ends_at is None or now < g.ends_at)
                for g in self.grants
            )
        )


class GrantEnvelope(BaseModel):
    cedar_ember: GrantStatus


class ClaimAnswer(BaseModel):
    result: Literal[
        "reset", "already_used", "not_limited", "cooldown", "ineligible", "unavailable", "rate_limited", "auth_error"
    ]
    resets_left: Count | None = None
    cleared: list[ResetWindow] = Field(default_factory=list)


class ConsumeGrant(DashboardModel):
    grant_id: GrantId
    operation_id: UUID
    confirmed: Literal[True]
    acknowledge_uncertain: bool = False


class OperationView(DashboardModel):
    operation_id: str
    grant_id: str
    created_at: datetime
    retry_until: datetime
    lease_until: datetime
    result: ClaimAnswer | None


class GrantsView(DashboardModel):
    status: GrantStatus | None
    error: str | None = None
    operations: list[OperationView]


class ConsumeView(DashboardModel):
    operation: OperationView
    refresh_complete: bool = False
