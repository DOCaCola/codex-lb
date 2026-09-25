from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator

from app.modules.shared.schemas import DashboardModel

OPENROUTER_KIND = "openrouter"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_CONTEXT_CAP = 262_144


class ReasoningMetadata(BaseModel):
    mandatory: bool = False
    default_enabled: bool | None = None
    supported_efforts: list[str] | None = None
    default_effort: str | None = None


class ModelArchitecture(BaseModel):
    input_modalities: list[str] = Field(default_factory=lambda: ["text"])
    output_modalities: list[str] = Field(default_factory=lambda: ["text"])


class ModelPricing(BaseModel):
    prompt: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    completion: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    input_cache_read: float | None = Field(default=None, ge=0, allow_inf_nan=False)

    @field_validator("prompt", "completion", "input_cache_read", mode="before")
    @classmethod
    def dynamic_price(cls, value: object) -> object:
        # OpenRouter uses -1 for dynamically routed models, not a negative cost.
        return None if value in (-1, "-1") else value


class TopProvider(BaseModel):
    context_length: int | None = Field(default=None, gt=0)
    max_completion_tokens: int | None = Field(default=None, gt=0)


class CatalogModel(BaseModel):
    id: str = Field(min_length=1)
    name: str
    context_length: int = Field(gt=0)
    architecture: ModelArchitecture
    pricing: ModelPricing
    top_provider: TopProvider
    supported_parameters: list[str] = Field(default_factory=list)
    reasoning: ReasoningMetadata | None = None
    expiration_date: str | None = None


class CatalogResponse(BaseModel):
    data: list[CatalogModel]


class FreeRequests(BaseModel):
    used: int = Field(ge=0)
    limit: int = Field(ge=0)
    remaining: int = Field(ge=0)


class KeyInfo(BaseModel):
    limit: float | None = None
    limit_remaining: float | None = None
    limit_reset: str | None = None
    usage: float
    usage_daily: float
    usage_weekly: float
    usage_monthly: float
    is_free_tier: bool
    is_management_key: bool = False
    organization_id: str | None = None
    creator_user_id: str | None = None
    workspace_id: str | None = None
    free_model_daily_requests: FreeRequests | None = None


class KeyResponse(BaseModel):
    data: KeyInfo


class CreditInfo(BaseModel):
    total_credits: float
    total_usage: float


class CreditResponse(BaseModel):
    data: CreditInfo


class ModelSelection(DashboardModel):
    model: str = Field(min_length=1, max_length=255)
    context_window: int = Field(default=DEFAULT_CONTEXT_CAP, gt=0)
    max_output_tokens: int | None = Field(default=None, gt=0)
    display_name: str | None = Field(default=None, max_length=255)


class AccountState(BaseModel):
    model_config = ConfigDict(extra="forbid")
    selections: list[ModelSelection] = Field(default_factory=list)
    catalog: list[CatalogModel] = Field(default_factory=list)
    catalog_updated_at: datetime | None = None
    catalog_error: str | None = None
    key: KeyInfo | None = None
    key_updated_at: datetime | None = None
    key_error: str | None = None
    credits: CreditInfo | None = None
    credits_updated_at: datetime | None = None
    credits_error: str | None = None


class OpenRouterCreate(DashboardModel):
    name: str = Field(min_length=1, max_length=128)
    api_key: SecretStr = Field(min_length=1)
    management_key: SecretStr | None = None


class OpenRouterUpdate(DashboardModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    is_enabled: bool | None = None
    api_key: SecretStr | None = None
    management_key: SecretStr | None = None
    selections: list[ModelSelection] | None = None


class OpenRouterAccountResponse(DashboardModel):
    id: str
    name: str
    is_enabled: bool
    has_management_key: bool
    state: AccountState


class OpenRouterAccountsResponse(DashboardModel):
    accounts: list[OpenRouterAccountResponse]
