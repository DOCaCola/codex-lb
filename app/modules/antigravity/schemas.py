from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator

from app.db.models import AccountRoutingPolicy
from app.modules.shared.schemas import DashboardModel

Effort = Literal["low", "medium", "high"]
EFFORTS: tuple[Effort, ...] = ("low", "medium", "high")
QuotaFamily = Literal["gemini", "argon", "claude"]
QuotaWindowName = Literal["five_hour", "weekly"]
PlanType = Literal["free", "pro", "ultra_5x", "ultra_20x", "unknown"]
# Lasting account states that need the operator; verification is a short cooldown instead (OmniRoute).
Hold = Literal["banned", "misconfigured", "location_unsupported"]


class Credentials(BaseModel):
    model_config = ConfigDict(hide_input_in_errors=True)
    access_token: SecretStr = Field(min_length=1)
    refresh_token: SecretStr = Field(min_length=1)
    expires_at: datetime

    @field_validator("expires_at")
    @classmethod
    def aware_expiry(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("Credential expiry must include a timezone")
        return value.astimezone(UTC)


class UserInfo(BaseModel):
    id: str = Field(min_length=1)
    email: str = Field(min_length=1)


class Tier(BaseModel):
    id: str
    name: str | None = None


class Credit(BaseModel):
    credit_type: str
    amount: float
    minimum_for_usage: float | None = None


class Subscription(BaseModel):
    current_tier: Tier | None = None
    paid_tier: Tier | None = None
    credits: list[Credit] = Field(default_factory=list)
    observed_at: datetime


class CatalogFamily(BaseModel):
    """One client-facing model: a tiered effort family or a standalone wire model."""

    id: str = Field(min_length=1)
    display_name: str
    # Effort tier -> wire model id; empty for a standalone model (whose wire id is the family id).
    tiers: dict[Effort, str] = Field(default_factory=dict)
    # Wire model id -> the catalog's model enum, which the native client reports in its labels.
    model_enums: dict[str, str] = Field(default_factory=dict)
    api_provider: str | None = None
    quota_family: QuotaFamily
    context_window: int | None = Field(default=None, gt=0)
    max_output_tokens: int | None = Field(default=None, gt=0)
    supports_images: bool = False
    supports_thinking: bool = False
    # Display-only per-wire-model quota readings from fetchAvailableModels.
    model_quota: dict[str, ModelQuotaReading] = Field(default_factory=dict)

    @property
    def anthropic_wire(self) -> bool:
        return self.api_provider == "API_PROVIDER_ANTHROPIC_VERTEX"


class ModelQuotaReading(BaseModel):
    remaining_fraction: float = Field(ge=0, le=1)
    resets_at: datetime | None = None


class QuotaBucket(BaseModel):
    family: QuotaFamily
    window: QuotaWindowName
    remaining_fraction: float = Field(ge=0, le=1)
    resets_at: datetime | None = None

    @property
    def used_percent(self) -> float:
        return round((1 - self.remaining_fraction) * 100, 4)


class MetadataState(BaseModel):
    updated_at: datetime | None = None
    error: str | None = None
    retry_at: datetime | None = None


class VerificationNotice(BaseModel):
    """Google's account-verification challenge; the link is shown to operators, never logged."""

    url: str | None
    observed_at: datetime


class AccountState(BaseModel):
    subscription: Subscription | None = None
    catalog: list[CatalogFamily] = Field(default_factory=list)
    default_model: str | None = None
    quota: list[QuotaBucket] = Field(default_factory=list)
    all_models: bool = True
    selections: list[str] = Field(default_factory=list)
    metadata: dict[Literal["account", "catalog", "quota"], MetadataState] = Field(default_factory=dict)
    verification: VerificationNotice | None = None


class WindowStatus(DashboardModel):
    family: QuotaFamily
    window: QuotaWindowName
    used_percent: float
    resets_at: datetime | None
    exhausted: bool


class Cooldown(DashboardModel):
    scope: str
    until: datetime
    reason: str


class AntigravityAccountResponse(DashboardModel):
    id: str
    name: str
    email: str
    project_id: str | None
    is_enabled: bool
    routing_policy: AccountRoutingPolicy
    max_concurrency: int | None
    credential_status: str
    hold: Hold | None
    hold_reason: str | None
    hold_at: datetime | None
    expires_at: datetime
    plan_type: PlanType
    quota_weight: int | None
    state: AccountState
    windows: list[WindowStatus]
    quota_fresh: bool
    cooldowns: list[Cooldown]


class AntigravityAccountsResponse(DashboardModel):
    accounts: list[AntigravityAccountResponse]


class OAuthStart(DashboardModel):
    name: str = Field(min_length=1, max_length=128)
    source_id: str | None = None


class OAuthStarted(DashboardModel):
    state: str
    authorization_url: str
    expires_at: datetime


class OAuthComplete(DashboardModel):
    state: str = Field(min_length=32, max_length=128)
    code: SecretStr = Field(min_length=1, max_length=4096)


class AntigravityImport(DashboardModel):
    name: str = Field(min_length=1, max_length=128)
    # A credential file in agy, OmniRoute or CLIProxyAPI shape; only its refresh token is used.
    credentials: dict[str, object] = Field(repr=False)


class AntigravityReconnect(DashboardModel):
    credentials: dict[str, object] = Field(repr=False)


class AntigravityUpdate(DashboardModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    is_enabled: bool | None = None
    routing_policy: AccountRoutingPolicy | None = None
    max_concurrency: int | None = Field(default=None, gt=0, strict=True)
    all_models: bool | None = None
    selections: list[str] | None = None
    clear_hold: bool = False


CatalogFamily.model_rebuild()
