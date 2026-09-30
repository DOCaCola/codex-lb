"""Operator reasoning policy, independent of model membership/capabilities."""

from typing import Annotated, Literal

from pydantic import AfterValidator, Field

ReasoningEffort = Literal["none", "minimal", "low", "medium", "high", "xhigh", "max", "ultra"]


def _unique_efforts(value: list[ReasoningEffort]) -> list[ReasoningEffort]:
    if len(value) != len(set(value)):
        raise ValueError("Select each reasoning effort once")
    return value


AllowedEfforts = Annotated[list[ReasoningEffort], Field(min_length=1), AfterValidator(_unique_efforts)]
ReasoningRestrictions = dict[str, AllowedEfforts]


def reasoning_allowed(allowed: list[str] | None, requested: str | None, default: str | None) -> bool:
    return allowed is None or (requested if requested is not None else default) in allowed
