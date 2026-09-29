"""Explicit model policies shared by catalog and protocol projection.

Dated snapshots of a known model inherit its policy; an unknown minor model
does not automatically inherit request features from its family name.

Reasoning capabilities come from Claude's own model catalog when it reports
them; the policy table is the fallback for catalog entries stored before
capabilities were recorded.
"""

import re
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

# Every effort Claude's ``output_config.effort`` accepts, lightest first.
EFFORT_LEVELS = ("low", "medium", "high", "xhigh", "max")
# Budget-thinking models map these onto ``budget_tokens`` (see protocol).
BUDGET_LEVELS = ("low", "medium", "high", "max")
# Claude's API default effort is ``high`` except where listed here.
_API_DEFAULT_EFFORT = {"claude-opus-5-5": "medium"}


@dataclass(frozen=True)
class ModelPolicy:
    mid_system: bool = False
    adaptive_reasoning: bool = False
    budget_reasoning: bool = False
    structured_output: bool = False

    @property
    def supports_reasoning(self) -> bool:
        return self.adaptive_reasoning or self.budget_reasoning


_POLICIES = {
    "claude-opus-5-5": ModelPolicy(mid_system=True, adaptive_reasoning=True, structured_output=True),
    "claude-sonnet-5-5": ModelPolicy(mid_system=True, adaptive_reasoning=True, structured_output=True),
    "claude-opus-5": ModelPolicy(mid_system=True, adaptive_reasoning=True, structured_output=True),
    "claude-sonnet-5": ModelPolicy(mid_system=True, adaptive_reasoning=True, structured_output=True),
    "claude-opus-4-6": ModelPolicy(adaptive_reasoning=True, structured_output=True),
    "claude-sonnet-4-6": ModelPolicy(adaptive_reasoning=True, structured_output=True),
    "claude-sonnet-4-5": ModelPolicy(budget_reasoning=True, structured_output=True),
    "claude-haiku-4-5": ModelPolicy(budget_reasoning=True, structured_output=True),
}


def _base_model(model: str) -> str:
    return re.sub(r"-\d{8}$", "", model.removeprefix("anthropic/"))


def model_policy(model: str) -> ModelPolicy | None:
    return _POLICIES.get(_base_model(model))


class CatalogCapabilities(BaseModel):
    """Reasoning capabilities Claude's ``/v1/models`` reports for one model."""

    model_config = ConfigDict(frozen=True)

    effort_levels: tuple[str, ...] = ()
    adaptive_thinking: bool = False
    budget_thinking: bool = False

    @model_validator(mode="before")
    @classmethod
    def from_catalog_tree(cls, value: object) -> object:
        # The API reports a nested tree with ``supported`` leaves; the flattened
        # form is what round-trips through stored account state.
        if not isinstance(value, dict) or not ({"effort", "thinking"} & value.keys()):
            return value

        def supported(node: object) -> bool:
            return isinstance(node, dict) and node.get("supported") is True

        effort = value.get("effort")
        thinking = value.get("thinking")
        types = thinking.get("types") if isinstance(thinking, dict) else None
        types = types if isinstance(types, dict) else {}
        return {
            # Levels the protocol does not know are dropped rather than forwarded.
            "effort_levels": tuple(
                level for level in EFFORT_LEVELS if supported(effort) and supported(effort.get(level))
            )
            if isinstance(effort, dict)
            else (),
            "adaptive_thinking": supported(types.get("adaptive")),
            "budget_thinking": supported(types.get("enabled")),
        }


@dataclass(frozen=True)
class ReasoningSpec:
    mode: Literal["adaptive", "budget"]
    levels: tuple[str, ...]
    default: str

    def effective_effort(self, effort: str) -> str | None:
        """The effort to send for a requested one, or None if it cannot be honored.

        Unsupported ``xhigh``/``max`` step down to ``high``; they are never
        escalated (``xhigh`` is not silently sent as the costlier ``max``).
        """
        if effort in self.levels:
            return effort
        if effort in ("xhigh", "max") and "high" in self.levels:
            return "high"
        return None


def reasoning_spec(model: str, capabilities: CatalogCapabilities | None) -> ReasoningSpec | None:
    """Reasoning a Claude model supports: catalog capabilities first, policy as fallback."""
    if capabilities is not None:
        if capabilities.adaptive_thinking and capabilities.effort_levels:
            mode: Literal["adaptive", "budget"] = "adaptive"
            levels = capabilities.effort_levels
        elif capabilities.budget_thinking:
            mode, levels = "budget", BUDGET_LEVELS
        else:
            return None
    else:
        policy = model_policy(model)
        if policy is None or not policy.supports_reasoning:
            return None
        mode = "adaptive" if policy.adaptive_reasoning else "budget"
        levels = BUDGET_LEVELS
    preferred = _API_DEFAULT_EFFORT.get(_base_model(model), "high") if mode == "adaptive" else "medium"
    default = preferred if preferred in levels else levels[0]
    return ReasoningSpec(mode=mode, levels=levels, default=default)
