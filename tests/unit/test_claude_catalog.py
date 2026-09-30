import json
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from app.modules.claude.client import ClaudeClient
from app.modules.claude.credentials import ClaudeError
from app.modules.claude.schemas import AccountState, CatalogModel, CatalogPage, ModelSelection
from app.modules.claude.service import project_models

pytestmark = pytest.mark.unit


async def test_catalog_pagination_uses_cursor_without_exposing_credentials():
    provider = ClaudeClient()
    provider._get = AsyncMock(
        side_effect=[
            CatalogPage(data=[CatalogModel(id="claude-first", display_name="First")], has_more=True, last_id="a/b+"),
            CatalogPage(data=[CatalogModel(id="claude-second", display_name="Second")], has_more=False),
        ]
    )
    models = await provider.catalog("secret", "2.1.282")
    assert [model.id for model in models] == ["claude-first", "claude-second"]
    assert provider._get.call_args_list[1].args[0] == "/v1/models?limit=100&after_id=a%2Fb%2B"


@pytest.mark.parametrize(
    "pages",
    [
        [CatalogPage(data=[], has_more=True)],
        [CatalogPage(data=[], has_more=True, last_id="same")] * 2,
        [
            CatalogPage(
                data=[
                    CatalogModel(id="duplicate", display_name="First"),
                    CatalogModel(id="duplicate", display_name="Second"),
                ],
                has_more=False,
            )
        ],
    ],
)
async def test_inconsistent_pagination_rejected(pages):
    provider = ClaudeClient()
    provider._get = AsyncMock(side_effect=pages)
    with pytest.raises(ClaudeError):
        await provider.catalog("secret", "2.1.282")


def test_projection_only_selected_models_and_retains_missing_selection():
    observed = AccountState(
        catalog=[CatalogModel(id="new", display_name="New")], selections=[ModelSelection(model="missing")]
    )
    projected = project_models(observed)
    assert len(projected) == 1
    assert projected[0].model == "anthropic/missing"
    assert not projected[0].is_enabled
    assert observed.selections[0].model == "missing"


def test_all_mode_preserves_disabled_claim_for_missing_reasoning_configuration():
    state = AccountState(all_models=True, reasoning_restrictions={"missing": ["high"]})
    row = project_models(state)[0]
    assert row.model == "anthropic/missing"
    assert not row.is_enabled
    assert json.loads(row.raw_metadata_json)["allowed_reasoning_efforts"] == ["high"]
    state.all_models = False
    assert project_models(state) == []


def test_discovery_limits_override_registry_without_persisted_client_budgets():
    model = CatalogModel(id="claude-opus-5", display_name="Opus", max_input_tokens=750000, max_tokens=96000)
    state = AccountState(catalog=[model], selections=[ModelSelection(model=model.id)])
    projected = project_models(state)[0]
    assert projected.context_window == 750000
    assert projected.max_output_tokens == 96000
    assert projected.is_enabled
    assert projected.raw_metadata_json is not None
    metadata = json.loads(projected.raw_metadata_json)
    assert "auto_compact_token_limit" not in metadata
    assert "effective_context_window_percent" not in metadata
    assert state.model_dump()["selections"] == [{"model": "claude-opus-5"}]


def test_missing_fields_use_only_exact_maintained_models():
    known = CatalogModel(id="claude-haiku-4-5-20251001", display_name="Haiku", max_tokens=32000)
    assert known.max_input_tokens == 200000 and known.max_tokens == 32000
    unknown = CatalogModel(id="claude-opus-5-99", display_name="Unknown", max_input_tokens=1000000)
    assert unknown.token_limits is None
    state = AccountState(catalog=[unknown], selections=[ModelSelection(model=unknown.id)])
    assert not project_models(state)[0].is_enabled


def test_haiku_budget_reasoning_is_advertised_with_dated_api_price():
    model = CatalogModel(id="claude-haiku-4-5-20251001", display_name="Haiku")
    projected = project_models(AccountState(catalog=[model], selections=[ModelSelection(model=model.id)]))[0]
    assert projected.input_per_1m == 1
    assert projected.cached_input_per_1m == 0.1
    metadata = json.loads(projected.raw_metadata_json)
    assert metadata["supports_reasoning"] is True
    assert metadata["supported_reasoning_levels"] == ["low", "medium", "high", "max"]


def _caps(levels: tuple[str, ...], *, adaptive: bool, budget: bool) -> dict:
    """Claude /v1/models capability tree, as returned over the OAuth path (2026-09-29)."""
    effort = {"supported": bool(levels)} | {
        level: {"supported": level in levels} for level in ("low", "medium", "high", "xhigh", "max")
    }
    return {
        "effort": effort,
        "thinking": {
            "supported": True,
            "types": {"adaptive": {"supported": adaptive}, "enabled": {"supported": budget}},
        },
        "image_input": {"supported": True},
    }


FULL = ("low", "medium", "high", "xhigh", "max")


@pytest.mark.parametrize(
    "model_id,capabilities,levels,default",
    [
        ("claude-opus-5-5", _caps(FULL, adaptive=True, budget=False), list(FULL), "medium"),
        ("claude-sonnet-5-5", _caps(FULL, adaptive=True, budget=False), list(FULL), "high"),
        (
            "claude-opus-4-6",
            _caps(("low", "medium", "high", "max"), adaptive=True, budget=True),
            ["low", "medium", "high", "max"],
            "high",
        ),
        (
            "claude-haiku-4-5-20251001",
            _caps((), adaptive=False, budget=True),
            ["low", "medium", "high", "max"],
            "medium",
        ),
    ],
)
def test_reasoning_levels_follow_catalog_capabilities(model_id, capabilities, levels, default):
    model = CatalogModel(id=model_id, display_name=model_id, capabilities=capabilities)
    state = AccountState(catalog=[model], selections=[ModelSelection(model=model_id)])
    # Stored account state round-trips the parsed capabilities.
    state = AccountState.model_validate_json(state.model_dump_json())
    metadata = json.loads(project_models(state)[0].raw_metadata_json)
    assert metadata["supports_reasoning"] is True
    assert metadata["supported_reasoning_levels"] == levels
    assert metadata["default_reasoning_level"] == default


def test_catalog_without_reasoning_capability_advertises_none():
    capabilities = _caps((), adaptive=False, budget=False)
    model = CatalogModel(id="claude-opus-5", display_name="Opus", capabilities=capabilities)
    metadata = json.loads(
        project_models(AccountState(catalog=[model], selections=[ModelSelection(model=model.id)]))[0].raw_metadata_json
    )
    assert metadata["supports_reasoning"] is False
    assert metadata["supported_reasoning_levels"] == []


@pytest.mark.parametrize("value", [0, -1, True, "64000", 1.5])
def test_invalid_discovered_limits_are_rejected(value):
    with pytest.raises(ValidationError):
        CatalogModel(id="claude-opus-5", display_name="Opus", max_tokens=value)


@pytest.mark.parametrize("field", ["contextWindow", "context_window", "maxOutputTokens", "max_output_tokens"])
def test_manual_limits_are_not_accepted(field):
    with pytest.raises(ValidationError):
        ModelSelection.model_validate({"model": "claude-opus-5", field: 10000})
