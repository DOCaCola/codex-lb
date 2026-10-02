"""Codex base instructions for routed (non-native) catalog rows.

Codex renders a catalog row's instruction template literally, so a routed row
without one would run with no Codex agent prompt at all. Routed rows instead
reuse the live native prompt of the model Codex treats as its default, with the
GPT identity neutralized so a Claude or OpenRouter model is not told it is a
GPT model.

The catalog prompt stays model-neutral because Codex replays a parent's stored
instructions into subagents running other models (opencodex #5217). The
destination model is named at request time instead, where it is known.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from app.core.openai.model_registry import UpstreamModel
from app.core.utils.json_guards import is_json_mapping

# Sub2API ``codexGPTIdentityPatterns``: covers "…an agent based on GPT-6.",
# "…a coding agent based on GPT-5." and "You are GPT-5.5 …" phrasings.
_GPT_IDENTITY_PATTERNS = (
    (re.compile(r",?\s*based on GPT-\d+(?:\.\d+)?(?:-[A-Za-z0-9]+)*"), ""),
    (re.compile(r"\bYou are GPT-\d+(?:\.\d+)?(?:-[A-Za-z0-9]+)*"), "You are Codex"),
)

# The neutral identity sentence ``neutralize_gpt_identity`` leaves behind.
_NEUTRAL_IDENTITY = re.compile(r"\bYou are Codex, (an agent|a coding agent)\.")


def native_instructions_template(model: UpstreamModel) -> str:
    """The instruction template Codex resolves for a native catalog row.

    ``model_messages.instructions_template`` is canonical; Codex promotes the
    legacy top-level ``base_instructions`` only when the template is absent.
    """
    messages = model.raw.get("model_messages")
    if is_json_mapping(messages):
        template = messages.get("instructions_template")
        if isinstance(template, str):
            return template
    return model.base_instructions


def neutralize_gpt_identity(instructions: str) -> str:
    for pattern, replacement in _GPT_IDENTITY_PATTERNS:
        instructions = pattern.sub(replacement, instructions)
    return instructions


def name_routed_identity(instructions: str, model_name: str) -> str:
    """Name the routed destination model in a Codex identity sentence.

    Handles both the neutral catalog prompt and a native GPT prompt a parent
    replayed into a routed subagent. Instructions without a Codex identity
    sentence are returned unchanged.
    """
    return _NEUTRAL_IDENTITY.sub(
        lambda match: f"You are Codex, {match.group(1)} running on {model_name}.",
        neutralize_gpt_identity(instructions),
    )


def routed_base_instructions(native_models: Iterable[UpstreamModel]) -> str | None:
    """Neutralized prompt of the default listed native model, if one has a prompt.

    Codex picks the lowest-priority listed model as its default; the slug
    breaks priority ties so every catalog build selects the same prompt.
    """
    candidates = sorted(
        (
            model
            for model in native_models
            if model.raw.get("visibility", "list") == "list" and native_instructions_template(model)
        ),
        key=lambda model: (model.priority, model.slug),
    )
    if not candidates:
        return None
    return neutralize_gpt_identity(native_instructions_template(candidates[0]))
