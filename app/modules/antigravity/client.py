"""Cloud Code metadata calls with the native CLI wire image (headers and bodies captured from agy 1.4.10)."""

from __future__ import annotations

import asyncio
import json
import math
import re
from datetime import UTC, datetime, timedelta
from typing import Any

import aiohttp
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from app.core.clients.http import lease_model_source_session
from app.core.types import JsonValue
from app.modules.antigravity.constants import API_VERSION, CLOUD_CODE_BASE_URL
from app.modules.antigravity.errors import AntigravityError, MetadataHTTPError
from app.modules.antigravity.version import ClientIdentity

MAX_METADATA_BYTES = 2 * 1024 * 1024
ONBOARD_ATTEMPTS = 5
ONBOARD_INTERVAL_SECONDS = 2.0
_DURATION = re.compile(r"^\s*(\d+(?:\.\d+)?)s\s*$")


def native_headers(access_token: str, identity: ClientIdentity) -> dict[str, str]:
    """Exactly the CLI's Cloud Code headers; aiohttp adds Host and the body framing."""
    return {
        "User-Agent": identity.user_agent,
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Accept-Encoding": "gzip",
    }


def method_url(method: str) -> str:
    return f"{CLOUD_CODE_BASE_URL}/{API_VERSION}:{method}"


def retry_seconds(value: str | None) -> float | None:
    """A google.protobuf.Duration ("2s", "11525.3s") or an integral Retry-After value."""
    if value is None:
        return None
    match = _DURATION.match(value)
    if match is not None:
        return float(match.group(1))
    return float(value) if value.strip().isdecimal() else None


def retry_info(body: JsonValue) -> float | None:
    error = body.get("error") if isinstance(body, dict) else None
    details = error.get("details") if isinstance(error, dict) else None
    for detail in details if isinstance(details, list) else []:
        if isinstance(detail, dict) and str(detail.get("@type", "")).endswith("google.rpc.RetryInfo"):
            delay = detail.get("retryDelay")
            return retry_seconds(delay) if isinstance(delay, str) else None
    return None


class Tier(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    name: str | None = None
    is_default: bool = Field(default=False, alias="isDefault")


class Credit(BaseModel):
    model_config = ConfigDict(extra="ignore")
    credit_type: str = Field(alias="creditType")
    credit_amount: float = Field(alias="creditAmount")
    minimum_for_usage: float | None = Field(default=None, alias="minimumCreditAmountForUsage")


class PaidTier(Tier):
    available_credits: list[Credit] = Field(default_factory=list, alias="availableCredits")


class LoadCodeAssist(BaseModel):
    model_config = ConfigDict(extra="ignore")
    current_tier: Tier | None = Field(default=None, alias="currentTier")
    paid_tier: PaidTier | None = Field(default=None, alias="paidTier")
    allowed_tiers: list[Tier] = Field(default_factory=list, alias="allowedTiers")
    project: str | None = Field(default=None, alias="cloudaicompanionProject")

    @field_validator("project", mode="before")
    @classmethod
    def project_id(cls, value: Any) -> Any:
        # Reported as a bare ID or as {"id": ..., "name": ...}.
        if isinstance(value, dict):
            return value.get("id")
        return value or None

    def onboarding_tier(self) -> str:
        default = next((tier.id for tier in self.allowed_tiers if tier.is_default), None)
        tier = default or (self.current_tier.id if self.current_tier else None)
        if tier is None:
            raise AntigravityError("Antigravity reported no tier to onboard this account", status_code=502)
        return tier


class OnboardOperation(BaseModel):
    model_config = ConfigDict(extra="ignore")
    done: bool = False
    response: dict[str, Any] | None = None

    @property
    def project(self) -> str | None:
        project = (self.response or {}).get("cloudaicompanionProject")
        if isinstance(project, dict):
            project = project.get("id")
        return project if isinstance(project, str) and project else None


class CloudCodeClient:
    def __init__(self, identity: ClientIdentity) -> None:
        self.identity = identity

    async def call(self, method: str, access_token: str, body: dict[str, JsonValue]) -> dict[str, JsonValue]:
        try:
            async with lease_model_source_session() as session:
                async with session.post(
                    method_url(method),
                    data=json.dumps(body, separators=(",", ":")).encode(),
                    headers=native_headers(access_token, self.identity),
                    timeout=aiohttp.ClientTimeout(total=30, connect=10),
                    allow_redirects=False,
                ) as response:
                    raw = await response.content.read(MAX_METADATA_BYTES + 1)
                    if len(raw) > MAX_METADATA_BYTES:
                        raise AntigravityError(f"Antigravity {method} exceeded the size limit", status_code=502)
                    try:
                        data = json.loads(raw) if raw else {}
                    except ValueError:
                        data = None
                    if response.status != 200:
                        delay = retry_info(data) or retry_seconds(response.headers.get("Retry-After"))
                        retry_at = datetime.now(UTC) + timedelta(seconds=math.ceil(delay)) if delay else None
                        raise MetadataHTTPError(method, response.status, retry_at, body=data)
                    if not isinstance(data, dict):
                        raise AntigravityError(f"Antigravity {method} returned invalid JSON", status_code=502)
                    return data
        except (aiohttp.ClientError, TimeoutError) as exc:
            raise AntigravityError(
                f"Antigravity {method} is unreachable: {type(exc).__name__}", status_code=503
            ) from exc

    async def load_code_assist(self, access_token: str) -> LoadCodeAssist:
        data = await self.call("loadCodeAssist", access_token, {"metadata": {"ideType": "ANTIGRAVITY"}})
        try:
            return LoadCodeAssist.model_validate(data)
        except ValidationError as exc:
            raise AntigravityError("Antigravity loadCodeAssist returned an invalid response", status_code=502) from exc

    async def onboard(self, access_token: str, tier_id: str) -> str:
        """Provision the account's managed project, polling the long-running operation briefly."""
        body: dict[str, JsonValue] = {
            "tier_id": tier_id,
            "metadata": {
                "ide_type": "ANTIGRAVITY",
                "ide_name": "antigravity",
                "ide_version": self.identity.version,
            },
        }
        for attempt in range(ONBOARD_ATTEMPTS):
            try:
                operation = OnboardOperation.model_validate(await self.call("onboardUser", access_token, body))
            except ValidationError as exc:
                raise AntigravityError("Antigravity onboarding returned an invalid response", status_code=502) from exc
            if operation.done:
                if operation.project is None:
                    raise AntigravityError("Antigravity onboarding finished without a project", status_code=502)
                return operation.project
            if attempt + 1 < ONBOARD_ATTEMPTS:
                await asyncio.sleep(ONBOARD_INTERVAL_SECONDS)
        raise AntigravityError("Antigravity onboarding did not finish; refresh the account later", status_code=503)

    async def available_models(self, access_token: str, project: str) -> dict[str, JsonValue]:
        return await self.call("fetchAvailableModels", access_token, {"project": project})

    async def quota_summary(self, access_token: str, project: str) -> dict[str, JsonValue]:
        return await self.call("retrieveUserQuotaSummary", access_token, {"project": project})
