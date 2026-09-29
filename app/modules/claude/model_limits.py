"""Automatic Claude token capabilities, distinct from request defaults.

Discovery wins. Maintained metadata only fills missing fields for exact known
models (including their dated snapshots), never inferred future family members.
Sources: authenticated Models API observed 2026-09-29; OpenCodex 8a005dd98.
"""

import re

from pydantic import BaseModel


class ModelTokenLimits(BaseModel):
    context_window: int
    max_output_tokens: int


_KNOWN_LIMITS = {
    "claude-sonnet-5-5": (1_000_000, 128_000),
    "claude-opus-5-5": (1_000_000, 128_000),
    "claude-fable-5-1": (1_000_000, 128_000),
    "claude-opus-5": (1_000_000, 128_000),
    "claude-sonnet-5": (1_000_000, 128_000),
    "claude-opus-4-6": (1_000_000, 128_000),
    "claude-sonnet-4-6": (1_000_000, 64_000),
    "claude-opus-4-5": (200_000, 64_000),
    "claude-sonnet-4-5": (1_000_000, 64_000),
    "claude-haiku-4-5": (200_000, 64_000),
}


def resolve_token_limits(model: str, max_input_tokens: int | None, max_tokens: int | None) -> ModelTokenLimits | None:
    known = _KNOWN_LIMITS.get(re.sub(r"-\d{8}$", "", model))
    context = max_input_tokens if max_input_tokens is not None else known[0] if known else None
    output = max_tokens if max_tokens is not None else known[1] if known else None
    if context is None or output is None:
        return None
    return ModelTokenLimits(context_window=context, max_output_tokens=output)


def default_output_tokens(maximum: int) -> int:
    # OpenCodex #3332/#3474: 8192 truncated answers and provoked client retries.
    # A request budget is not the model ceiling; explicit budgets remain intact.
    return min(64_000, maximum)
