import json

import pytest

from app.modules.openrouter.catalog import project_models
from app.modules.openrouter.schemas import AccountState, CatalogModel, ModelPricing, ModelSelection, ReasoningMetadata

pytestmark = pytest.mark.unit


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
