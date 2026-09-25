from unittest.mock import AsyncMock

import pytest

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
