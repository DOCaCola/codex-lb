from __future__ import annotations

import json
from dataclasses import dataclass, field

from pydantic import BaseModel, ConfigDict, Field

from app.core.clients.proxy import CodexControlResponse


class NativeImageInputUsage(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)
    cached_tokens: int | None = Field(default=None, ge=0)


class NativeImageUsage(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    input_tokens_details: NativeImageInputUsage | None = None

    @property
    def cached_input_tokens(self) -> int | None:
        return self.input_tokens_details.cached_tokens if self.input_tokens_details is not None else None


def reported_image_usage(response: CodexControlResponse) -> NativeImageUsage:
    if not 200 <= response.status_code < 300:
        return NativeImageUsage()
    try:
        body = json.loads(response.body)
        if isinstance(body, dict) and isinstance(body.get("usage"), dict):
            return NativeImageUsage.model_validate(body["usage"])
    except (ValueError, UnicodeDecodeError):
        pass
    # Missing or unreadable usage is not evidence of token consumption.
    return NativeImageUsage()


@dataclass
class NativeImageAccounting:
    """One request-owned usage snapshot for logging and quota settlement."""

    model: str
    usage: NativeImageUsage = field(default_factory=NativeImageUsage)

    def capture(self, response: CodexControlResponse) -> None:
        self.usage = reported_image_usage(response)
