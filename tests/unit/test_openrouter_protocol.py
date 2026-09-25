import json

import pytest

from app.core.openai.exceptions import ClientPayloadError
from app.db.models import ModelSource
from app.modules.model_sources.catalog import source_models_to_upstream_models
from app.modules.openrouter.catalog import project_models
from app.modules.openrouter.protocol import normalize_error, project_request
from app.modules.openrouter.schemas import AccountState, CatalogModel, ModelSelection

pytestmark = pytest.mark.unit


def source(parameters):
    model = CatalogModel.model_validate(
        {
            "id": "qwen/test:free",
            "name": "Test",
            "context_length": 262144,
            "architecture": {},
            "pricing": {},
            "top_provider": {},
            "supported_parameters": parameters,
            "reasoning": {"supported_efforts": ["xhigh", "medium", "low"], "default_effort": "xhigh"},
        }
    )
    return ModelSource(
        id="test",
        name="Test",
        kind="openrouter",
        is_enabled=True,
        models=project_models(AccountState(catalog=[model], selections=[ModelSelection(model=model.id)])),
    )


@pytest.mark.parametrize("supported", [False, True])
@pytest.mark.parametrize("value", [None, False, True])
@pytest.mark.parametrize("responses", [False, True])
def test_parallel_parameter_contract(supported, value, responses):
    provider = source(["tools", "reasoning"] + (["parallel_tool_calls"] if supported else []))
    payload = {"model": "openrouter/qwen/test:free"}
    if value is not None:
        payload["parallel_tool_calls"] = value
    original = dict(payload)
    if value is False and not supported:
        with pytest.raises(ClientPayloadError) as error:
            project_request(provider, payload, responses=responses)
        assert error.value.code == "unsupported_parameter"
        assert error.value.param == "parallel_tool_calls"
    else:
        result = project_request(provider, payload, responses=responses)
        assert result["model"] == "qwen/test:free"
        assert result["provider"] == {"sort": "price", "require_parameters": True}
        if supported and value is not None:
            assert result["parallel_tool_calls"] is value
        else:
            assert "parallel_tool_calls" not in result
    assert payload == original
    [catalog] = source_models_to_upstream_models([provider])
    assert catalog.supports_parallel_tool_calls is supported
    assert [level.effort for level in catalog.supported_reasoning_levels] == ["low", "medium", "xhigh"]
    assert catalog.default_reasoning_level == "xhigh"
    assert json.loads(provider.models[0].raw_metadata_json)["supported_parameters"][0] == "tools"


@pytest.mark.parametrize("code", [404, "model_not_found", None])
def test_errors_preserve_message_and_string_codes(code):
    payload = {"error": {"code": code, "message": "No endpoints found"}}
    normalized = normalize_error(payload, 404)
    assert normalized["error"] == {
        "code": str(code) if isinstance(code, int) else code,
        "message": "No endpoints found",
        "type": "invalid_request_error",
    }
    assert payload["error"]["code"] == code
