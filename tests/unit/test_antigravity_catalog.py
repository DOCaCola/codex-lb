from __future__ import annotations

from typing import Any

import pytest

from app.modules.antigravity.catalog import parse_catalog, quota_family, wire_model
from app.modules.antigravity.errors import AntigravityError


def _model(display: str, provider: str = "API_PROVIDER_GOOGLE_GEMINI", **extra: object) -> dict[str, Any]:
    return {"displayName": display, "apiProvider": provider, **extra}


CATALOG: dict[str, Any] = {
    "models": {
        "gemini-3.8-flash-low": _model("Gemini 3.8 Flash (Low)", maxTokens=1_048_576, maxOutputTokens=65_536),
        "gemini-3.8-flash-high": _model(
            "Gemini 3.8 Flash (High)",
            maxTokens=900_000,
            maxOutputTokens=65_536,
            supportsThinking=True,
            model="MODEL_PLACEHOLDER_M18",
            quotaInfo={"remainingFraction": 0.25, "resetTime": "2026-10-29T15:00:00Z"},
        ),
        "gemini-4-argon": _model("Gemini 4 Argon", maxTokens=1_048_576),
        "claude-sonnet-5": _model("Claude Sonnet 5", "API_PROVIDER_ANTHROPIC_VERTEX", maxTokens=200_000),
        "broken": {"maxTokens": -1},
    },
    "agentModelSorts": [
        {"groups": [{"modelIds": ["gemini-3.8-flash-high", "gemini-3.8-flash-low", "claude-sonnet-5"]}]},
        {"groups": [{"modelIds": ["gemini-4-argon"]}]},
    ],
    "defaultAgentModelId": "gemini-3.8-flash-high",
}


def test_tiers_merge_into_one_family_in_agent_order() -> None:
    families, default = parse_catalog(CATALOG)
    assert [family.id for family in families] == ["gemini-3.8-flash", "claude-sonnet-5", "gemini-4-argon"]
    flash = families[0]
    assert flash.display_name == "Gemini 3.8 Flash"
    assert flash.tiers == {"high": "gemini-3.8-flash-high", "low": "gemini-3.8-flash-low"}
    # Tiers share limits; the smallest keeps every tier valid.
    assert flash.context_window == 900_000
    assert flash.supports_thinking
    assert flash.model_enums == {"gemini-3.8-flash-high": "MODEL_PLACEHOLDER_M18"}
    assert flash.model_quota["gemini-3.8-flash-high"].remaining_fraction == 0.25
    assert default == "gemini-3.8-flash"


def test_quota_families() -> None:
    families = {family.id: family for family in parse_catalog(CATALOG)[0]}
    assert families["gemini-3.8-flash"].quota_family == "gemini"
    assert families["gemini-4-argon"].quota_family == "argon"
    assert families["claude-sonnet-5"].quota_family == "claude"
    assert families["claude-sonnet-5"].anthropic_wire
    assert quota_family("gpt-oss-120b-medium", "GPT-OSS 120B") == "claude"


def test_models_outside_the_agent_picker_are_not_offered() -> None:
    catalog = {**CATALOG, "models": {**CATALOG["models"], "tab_flash_lite": _model("Tab")}}
    assert "tab_flash_lite" not in {family.id for family in parse_catalog(catalog)[0]}


def test_models_the_account_cannot_call_are_not_offered() -> None:
    # A free account's catalog lists Argon as gemini-4-argon-disabled in the agent picker.
    models = {key: value for key, value in CATALOG["models"].items() if key != "gemini-4-argon"}
    catalog = {
        **CATALOG,
        "models": {
            **models,
            "gemini-4-argon-disabled": _model("Gemini 4 Argon", maxTokens=1_048_576),
            "gpt-oss-120b-medium": _model("GPT-OSS 120B", "API_PROVIDER_OPENAI_VERTEX", disabled=True),
            "internal-agent": _model("Internal", isInternal=True),
        },
        "agentModelSorts": [
            {"groups": [{"modelIds": ["gemini-4-argon-disabled", "gemini-3.8-flash-high", "gpt-oss-120b-medium"]}]},
            {"groups": [{"modelIds": ["internal-agent", "claude-sonnet-5"]}]},
        ],
        "defaultAgentModelId": "gemini-4-argon-disabled",
    }
    families, default = parse_catalog(catalog)
    assert [family.id for family in families] == ["gemini-3.8-flash", "claude-sonnet-5"]
    assert default is None


def test_family_mixing_providers_is_rejected() -> None:
    catalog: dict[str, Any] = {
        "models": {
            "x-low": _model("X (Low)"),
            "x-high": _model("X (High)", "API_PROVIDER_ANTHROPIC_VERTEX"),
        }
    }
    with pytest.raises(AntigravityError, match="mixes providers"):
        parse_catalog(catalog)


def test_missing_catalog_is_an_upstream_error() -> None:
    with pytest.raises(AntigravityError) as raised:
        parse_catalog({})
    assert raised.value.status_code == 502


@pytest.mark.parametrize(
    ("effort", "wire", "level"),
    [
        (None, "gemini-3.8-flash-high", "high"),
        ("xhigh", "gemini-3.8-flash-high", "high"),
        ("none", "gemini-3.8-flash-low", "low"),
        ("low", "gemini-3.8-flash-low", "low"),
        # Medium is not advertised; a tie prefers the higher level.
        ("medium", "gemini-3.8-flash-high", "high"),
    ],
)
def test_wire_model_picks_the_nearest_advertised_tier(effort: str | None, wire: str, level: str) -> None:
    flash = parse_catalog(CATALOG)[0][0]
    assert wire_model(flash, effort) == (wire, level)


def test_standalone_models_ignore_effort() -> None:
    argon = next(family for family in parse_catalog(CATALOG)[0] if family.id == "gemini-4-argon")
    assert wire_model(argon, "high") == ("gemini-4-argon", None)


def test_unknown_effort_is_rejected() -> None:
    with pytest.raises(AntigravityError):
        wire_model(parse_catalog(CATALOG)[0][0], "turbo")
