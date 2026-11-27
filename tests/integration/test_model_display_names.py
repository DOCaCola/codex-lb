from __future__ import annotations

import json

import pytest

from app.core.openai.model_registry import get_model_registry
from tests.integration.test_settings_audit_changed_fields import _wait_for_settings_changed_audit_log
from tests.integration.test_v1_models import _create_model_source, _make_upstream_model

pytestmark = pytest.mark.integration

_CATALOGUE_PATH = "/api/settings/model-context-window-overrides"
_NAMES_PATH = "/api/settings/model-display-names"


def _entry(body: dict, slug: str) -> dict:
    return next(model for model in body["models"] if model["slug"] == slug)


@pytest.mark.asyncio
async def test_operator_name_replaces_the_provider_name_in_every_model_list(async_client):
    await get_model_registry().update({"pro": [_make_upstream_model("gpt-new")]})
    await _create_model_source(async_client, name="named-src", model="external-model", supports_responses=True)

    for slug, name in (("gpt-new", "House GPT"), ("external-model", "House External")):
        renamed = await async_client.put(f"{_NAMES_PATH}/{slug}", json={"displayName": f"  {name}  "})
        assert renamed.status_code == 200, renamed.text
        entry = _entry(renamed.json(), slug)
        assert (entry["displayName"], entry["renamed"]) == (name, True)
    assert _entry(renamed.json(), "external-model")["providerDisplayName"] == "external-model"
    audit = await _wait_for_settings_changed_audit_log()
    assert audit.details is not None
    assert json.loads(audit.details)["changed_fields"] == ["model_display_names"]

    codex = (await async_client.get("/backend-api/codex/models")).json()
    entries = {entry["slug"]: entry for entry in codex["models"]}
    assert entries["gpt-new"]["display_name"] == "House GPT"
    assert entries["external-model"]["display_name"] == "House External"
    v1 = {item["id"]: item for item in (await async_client.get("/v1/models")).json()["data"]}
    assert v1["external-model"]["metadata"]["display_name"] == "House External"
    anthropic = await async_client.get(
        "/v1/models", params={"limit": 1000}, headers={"anthropic-version": "2023-06-01"}
    )
    assert "House External" in {entry["display_name"] for entry in anthropic.json()["data"]}
    dashboard = {model["id"]: model["name"] for model in (await async_client.get("/api/models")).json()["models"]}
    assert dashboard["gpt-new"] == "House GPT"
    assert dashboard["external-model"] == "House External"

    restored = await async_client.delete(f"{_NAMES_PATH}/external-model")
    assert restored.status_code == 200
    entry = _entry(restored.json(), "external-model")
    assert (entry["displayName"], entry["renamed"]) == ("external-model", False)
    codex = (await async_client.get("/backend-api/codex/models")).json()
    assert {entry["slug"]: entry["display_name"] for entry in codex["models"]}["external-model"] == "external-model"


@pytest.mark.asyncio
async def test_model_display_names_validate_the_model_and_name(async_client):
    await get_model_registry().update({"pro": [_make_upstream_model("gpt-new")]})

    unknown = await async_client.put(f"{_NAMES_PATH}/unknown-model", json={"displayName": "Name"})
    assert unknown.status_code == 400
    assert unknown.json()["error"]["code"] == "model_not_in_catalogue"
    blank = await async_client.put(f"{_NAMES_PATH}/gpt-new", json={"displayName": "   "})
    assert blank.status_code == 422
    missing = await async_client.delete(f"{_NAMES_PATH}/gpt-new")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "model_display_name_not_found"
