from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator

from app.modules.shared.schemas import DashboardModel

CLAUDE_KIND = "claude"
CLAUDE_BASE_URL = "https://api.anthropic.com"


class ProfileAccount(BaseModel):
    uuid: str = Field(min_length=1)


class ProfileOrganization(BaseModel):
    uuid: str = Field(min_length=1)


class AuthenticatedProfile(BaseModel):
    account: ProfileAccount
    organization: ProfileOrganization


class Credentials(BaseModel):
    model_config = ConfigDict(hide_input_in_errors=True)
    access_token: SecretStr = Field(min_length=1)
    refresh_token: SecretStr = Field(min_length=1)
    expires_at: datetime
    scopes: list[str]

    @field_validator("expires_at")
    @classmethod
    def aware_expiry(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("Credential expiry must include a timezone")
        return value.astimezone(UTC)


class ImportedOAuth(BaseModel):
    model_config = ConfigDict(hide_input_in_errors=True)
    accessToken: SecretStr = Field(min_length=1)
    refreshToken: SecretStr = Field(min_length=1)
    expiresAt: int = Field(strict=True, ge=1_000_000_000_000, le=9_999_999_999_999)
    scopes: list[str]

    @field_validator("scopes")
    @classmethod
    def inference_scope(cls, value: list[str]) -> list[str]:
        if "user:inference" not in value:
            raise ValueError("A user:inference grant is required")
        return value

    def credentials(self) -> Credentials:
        return Credentials(
            access_token=self.accessToken,
            refresh_token=self.refreshToken,
            expires_at=datetime.fromtimestamp(self.expiresAt / 1000, UTC),
            scopes=self.scopes,
        )


class CredentialFile(BaseModel):
    model_config = ConfigDict(hide_input_in_errors=True)
    claudeAiOauth: ImportedOAuth


class TokenResponse(BaseModel):
    model_config = ConfigDict(hide_input_in_errors=True)
    access_token: SecretStr = Field(min_length=1)
    refresh_token: SecretStr = Field(min_length=1)
    expires_in: int = Field(strict=True, gt=0, le=31_536_000)
    token_type: Literal["Bearer", "bearer"]
    scope: str

    def credentials(self, now: datetime) -> Credentials:
        scopes = self.scope.split()
        if "user:inference" not in scopes:
            raise ValueError("A user:inference grant is required")
        return Credentials(
            access_token=self.access_token,
            refresh_token=self.refresh_token,
            expires_at=now + timedelta(seconds=self.expires_in),
            scopes=scopes,
        )


class ModelSelection(DashboardModel):
    model: str = Field(min_length=1, max_length=255)
    context_window: int = Field(default=200_000, gt=0, le=262_144)
    max_output_tokens: int = Field(default=8192, gt=0)


class CatalogModel(BaseModel):
    id: str = Field(min_length=1)
    display_name: str
    created_at: datetime | None = None


class CatalogPage(BaseModel):
    data: list[CatalogModel]
    has_more: bool
    last_id: str | None = None


class QuotaWindow(BaseModel):
    utilization: float = Field(ge=0, allow_inf_nan=False)
    resets_at: datetime | None = None

    @field_validator("resets_at")
    @classmethod
    def aware_reset(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("Quota reset must include a timezone")
        return value.astimezone(UTC) if value is not None else None


class UsageSnapshot(BaseModel):
    # Preserve newer provider windows for display without guessing model ownership.
    model_config = ConfigDict(extra="allow")
    five_hour: QuotaWindow | None = None
    seven_day: QuotaWindow | None = None
    seven_day_opus: QuotaWindow | None = None
    seven_day_sonnet: QuotaWindow | None = None


class AccountState(BaseModel):
    selections: list[ModelSelection] = Field(default_factory=list)
    catalog: list[CatalogModel] = Field(default_factory=list)
    catalog_updated_at: datetime | None = None
    catalog_error: str | None = None
    usage: UsageSnapshot | None = None
    usage_updated_at: datetime | None = None
    usage_error: str | None = None


WindowName = Literal["five_hour", "seven_day", "seven_day_opus", "seven_day_sonnet"]


class WindowStatus(DashboardModel):
    name: WindowName
    utilization: float | None
    resets_at: datetime | None
    freshness: Literal["fresh", "stale", "unknown"]
    exhausted: bool


class ModelQuota(DashboardModel):
    model: str
    blocked: bool
    blocking_windows: list[WindowName] = Field(default_factory=list)
    retry_at: datetime | None = None


class QuotaStatus(DashboardModel):
    observed_at: datetime | None
    windows: list[WindowStatus]
    models: list[ModelQuota]


class ClaudeImport(DashboardModel):
    name: str = Field(min_length=1, max_length=128)
    credentials: CredentialFile = Field(repr=False)
    acknowledge_exclusive_refresh: Literal[True]


class ClaudeUpdate(DashboardModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    is_enabled: bool | None = None
    selections: list[ModelSelection] | None = None


class ClaudeAccountResponse(DashboardModel):
    id: str
    name: str
    is_enabled: bool
    credential_status: str
    expires_at: datetime
    state: AccountState
    quota: QuotaStatus


class ClaudeAccountsResponse(DashboardModel):
    accounts: list[ClaudeAccountResponse]


class OAuthStart(DashboardModel):
    name: str = Field(min_length=1, max_length=128)
    acknowledge_exclusive_refresh: Literal[True]
    source_id: str | None = None


class ClaudeReconnect(DashboardModel):
    credentials: CredentialFile = Field(repr=False)
    acknowledge_exclusive_refresh: Literal[True]


class OAuthStarted(DashboardModel):
    state: str
    authorization_url: str
    expires_at: datetime


class OAuthComplete(DashboardModel):
    state: str = Field(min_length=32, max_length=128)
    code: SecretStr = Field(min_length=1, max_length=4096)
