from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, SecretStr

from app.db.models import AccountRoutingPolicy
from app.modules.shared.schemas import DashboardModel

OPENAI_API_KIND = "openai_apikey"
OPENAI_API_BASE_URL = "https://api.openai.com/v1"
# opencodex's naming: bare ids stay the subscription pool, this prefix is the API-key identity.
OPENAI_API_MODEL_PREFIX = "openai-apikey/"

ModelKind = Literal["text", "image"]


class UpstreamModel(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(min_length=1)
    created: int | None = None
    owned_by: str | None = None


class ModelsResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    data: list[UpstreamModel]


class CatalogModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1)
    kind: ModelKind
    created: int | None = None


class ModelSelection(DashboardModel):
    model_config = ConfigDict(extra="forbid")
    model: str = Field(min_length=1, max_length=255)


class AccountState(BaseModel):
    model_config = ConfigDict(extra="forbid")
    selections: list[ModelSelection] = Field(default_factory=list)
    catalog: list[CatalogModel] = Field(default_factory=list)
    catalog_updated_at: AwareDatetime | None = None
    catalog_error: str | None = None
    monthly_credit_usd: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    credit_renews_on: int | None = Field(default=None, ge=1, le=31)


class OpenAIApiCreate(DashboardModel):
    name: str = Field(min_length=1, max_length=128)
    api_key: SecretStr = Field(min_length=1)
    monthly_credit_usd: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    credit_renews_on: int | None = Field(default=None, ge=1, le=31)


class OpenAIApiUpdate(DashboardModel):
    routing_policy: AccountRoutingPolicy | None = None
    name: str | None = Field(default=None, min_length=1, max_length=128)
    is_enabled: bool | None = None
    api_key: SecretStr | None = None
    selections: list[ModelSelection] | None = None
    # Explicit null clears the setting.
    monthly_credit_usd: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    credit_renews_on: int | None = Field(default=None, ge=1, le=31)


class CreditEstimate(DashboardModel):
    """Spend recorded by codex-lb against the monthly credit; OpenAI offers no balance endpoint for project keys."""

    cycle_start: datetime
    cycle_end: datetime
    spent_usd: float
    monthly_credit_usd: float | None
    remaining_usd: float | None
    # A billing refusal from OpenAI is authoritative over the estimate.
    exhausted_until: datetime | None


class OpenAIApiAccountResponse(DashboardModel):
    routing_policy: AccountRoutingPolicy = AccountRoutingPolicy.NORMAL
    id: str
    name: str
    is_enabled: bool
    state: AccountState
    # Published name per model id when the selection sets none.
    model_names: dict[str, str]
    credit: CreditEstimate


class OpenAIApiAccountsResponse(DashboardModel):
    accounts: list[OpenAIApiAccountResponse]
