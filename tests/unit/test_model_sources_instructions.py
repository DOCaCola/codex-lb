from __future__ import annotations

from dataclasses import replace

import pytest

from app.core.openai.model_registry import UpstreamModel
from app.core.types import JsonValue
from app.modules.model_sources.instructions import (
    name_routed_identity,
    native_instructions_template,
    neutralize_gpt_identity,
    routed_base_instructions,
)


def _model(
    slug: str,
    *,
    priority: int = 0,
    base_instructions: str = "",
    raw: dict[str, JsonValue] | None = None,
) -> UpstreamModel:
    return UpstreamModel(
        slug=slug,
        display_name=slug,
        description=slug,
        context_window=272_000,
        input_modalities=("text",),
        supported_reasoning_levels=(),
        default_reasoning_level=None,
        supports_reasoning_summaries=False,
        support_verbosity=False,
        default_verbosity=None,
        prefer_websockets=False,
        supports_parallel_tool_calls=True,
        supported_in_api=True,
        minimal_client_version=None,
        priority=priority,
        available_in_plans=frozenset({"pro"}),
        base_instructions=base_instructions,
        raw=raw or {"visibility": "list"},
    )


@pytest.mark.parametrize(
    ("native", "neutral"),
    [
        ("You are Codex, an agent based on GPT-6. Rules.", "You are Codex, an agent. Rules."),
        ("You are Codex, a coding agent based on GPT-5. Rules.", "You are Codex, a coding agent. Rules."),
        ("You are Codex, based on GPT-5.6-sol. Rules.", "You are Codex. Rules."),
        ("You are GPT-5.5, a model. Rules.", "You are Codex, a model. Rules."),
        ("No identity here.", "No identity here."),
    ],
)
def test_neutralize_gpt_identity(native: str, neutral: str) -> None:
    assert neutralize_gpt_identity(native) == neutral


@pytest.mark.parametrize(
    "instructions",
    ["You are Codex, an agent. Rules.", "You are Codex, an agent based on GPT-6. Rules."],
)
def test_name_routed_identity_names_neutral_and_replayed_native_prompts(instructions: str) -> None:
    assert name_routed_identity(instructions, "Claude Opus 5.5") == (
        "You are Codex, an agent running on Claude Opus 5.5. Rules."
    )


def test_name_routed_identity_leaves_other_instructions_unchanged() -> None:
    assert name_routed_identity("You are a helpful assistant.", "Claude Opus 5.5") == "You are a helpful assistant."


def test_native_template_prefers_model_messages_over_legacy_field() -> None:
    model = _model(
        "gpt",
        base_instructions="legacy",
        raw={"visibility": "list", "model_messages": {"instructions_template": "canonical"}},
    )

    assert native_instructions_template(model) == "canonical"
    assert native_instructions_template(replace(model, raw={"visibility": "list"})) == "legacy"


def test_routed_base_instructions_uses_lowest_priority_listed_prompt() -> None:
    models = [
        _model("gpt-b", priority=1, base_instructions="You are Codex, an agent based on GPT-6. B."),
        _model("gpt-a", priority=1, base_instructions="You are Codex, an agent based on GPT-6. A."),
        _model("gpt-hidden", priority=0, base_instructions="Hidden.", raw={"visibility": "hide"}),
        _model("gpt-empty", priority=0),
    ]

    assert routed_base_instructions(models) == "You are Codex, an agent. A."
    assert routed_base_instructions(reversed(models)) == "You are Codex, an agent. A."


def test_routed_base_instructions_without_native_prompt() -> None:
    assert routed_base_instructions([_model("gpt-empty")]) is None
