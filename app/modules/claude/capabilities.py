"""Explicit model policies shared by catalog and protocol projection.

Dated snapshots of a known model inherit its policy; an unknown minor model
does not automatically inherit request features from its family name.
"""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ModelPolicy:
    mid_system: bool = False
    adaptive_reasoning: bool = False
    structured_output: bool = False


_POLICIES = {
    "claude-opus-5": ModelPolicy(True, True, True),
    "claude-sonnet-5": ModelPolicy(True, True, True),
    "claude-opus-4-6": ModelPolicy(False, True, True),
    "claude-sonnet-4-6": ModelPolicy(False, True, True),
    "claude-sonnet-4-5": ModelPolicy(False, False, True),
    "claude-haiku-4-5": ModelPolicy(False, False, True),
}


def model_policy(model: str) -> ModelPolicy | None:
    name = re.sub(r"-\d{8}$", "", model.removeprefix("anthropic/"))
    return _POLICIES.get(name)
