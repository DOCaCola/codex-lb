import json

import pytest

from app.modules.openrouter.catalog import project_models
from app.modules.openrouter.schemas import AccountState, CatalogModel, ModelPricing, ModelSelection, ReasoningMetadata

pytestmark = pytest.mark.unit


def test_all_mode_preserves_overrides_removed_claims_and_explicit_image_selection():
    model = CatalogModel.model_validate(
        {"id": "text", "name": "Text", "context_length": 1000000, "architecture": {}, "pricing": {}, "top_provider": {}}
    )
    image = CatalogModel.model_validate(
        {
            "id": "image",
            "name": "Image",
            "architecture": {"output_modalities": ["image"]},
            "pricing": {},
            "top_provider": {},
            "image": {
                "id": "image",
                "name": "Image",
                "architecture": {"output_modalities": ["image"]},
                "supported_parameters": {},
            },
        }
    )
    state = AccountState(all_models=True, catalog=[model, image], selections=[ModelSelection(model="removed")])
    projected = project_models(state)
    assert [(row.model, row.is_enabled) for row in projected] == [
        ("openrouter/removed", False),
        ("openrouter/text", True),
    ]
    assert state.selections == [ModelSelection(model="removed")]
    state.selections.append(ModelSelection(model="text", context_window=100000))
    assert project_models(state)[1].context_window == 100000
    state.selections.append(ModelSelection(model="image"))
    assert project_models(state)[-1].model == "openrouter/image"


def test_all_mode_preserves_disabled_claim_for_missing_reasoning_configuration():
    state = AccountState(all_models=True, reasoning_restrictions={"missing": ["high"]})
    row = project_models(state)[0]
    assert row.model == "openrouter/missing"
    assert not row.is_enabled
    assert json.loads(row.raw_metadata_json)["allowed_reasoning_efforts"] == ["high"]
    state.all_models = False
    assert project_models(state) == []


@pytest.mark.parametrize(
    "efforts, expected",
    [(None, ["minimal", "low", "medium", "high", "xhigh", "max"]), ([], []), (["high", "none"], ["high"])],
)
def test_mandatory_reasoning_never_advertises_none(efforts, expected):
    model = CatalogModel.model_validate(
        {
            "id": "test",
            "name": "Test",
            "context_length": 1_000_000,
            "architecture": {},
            "pricing": {"prompt": "0.000001"},
            "top_provider": {"context_length": 500_000},
            "reasoning": {"mandatory": True, "supported_efforts": efforts},
        }
    )
    state = AccountState(catalog=[model], selections=[ModelSelection(model="test")])
    row = project_models(state)[0]
    assert row.context_window == 262144
    assert row.input_per_1m == 1
    assert row.raw_metadata_json is not None
    assert json.loads(row.raw_metadata_json)["supported_reasoning_levels"] == expected


def test_dynamic_pricing_is_unknown_not_free():
    assert ModelPricing(prompt="-1", completion="0").prompt is None
    assert ModelPricing(completion="0").completion == 0


def test_unspecified_efforts_survive_snapshot():
    metadata = ReasoningMetadata(mandatory=True)
    assert (
        "supported_efforts"
        not in ReasoningMetadata.model_validate_json(metadata.model_dump_json(exclude_unset=True)).model_fields_set
    )


@pytest.mark.parametrize(
    "parameters,reasoning,expected",
    [
        ([], None, "none"),
        (["reasoning"], {"default_enabled": False, "default_effort": "high"}, "none"),
        (["reasoning"], {"default_effort": "high"}, "high"),
        (["reasoning"], None, None),
    ],
)
def test_projected_default_does_not_invent_enabled_reasoning(parameters, reasoning, expected):
    model = CatalogModel.model_validate(
        {
            "id": "test",
            "name": "Test",
            "context_length": 100000,
            "architecture": {},
            "pricing": {},
            "top_provider": {},
            "supported_parameters": parameters,
            "reasoning": reasoning,
        }
    )
    state = AccountState(catalog=[model], selections=[ModelSelection(model="test")])
    metadata = json.loads(project_models(state)[0].raw_metadata_json)
    assert metadata.get("default_reasoning_level") == expected
