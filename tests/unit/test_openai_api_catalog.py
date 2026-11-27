from __future__ import annotations

from datetime import datetime

import pytest

from app.core.usage import pricing_catalog
from app.modules.openai_api.catalog import default_model_names, model_kind
from app.modules.openai_api.credit import credit_cycle
from app.modules.openai_api.schemas import AccountState, CatalogModel, ModelSelection

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("renews_on", "now", "expected"),
    [
        (1, datetime(2026, 11, 26, 12), (datetime(2026, 11, 1), datetime(2026, 12, 1))),
        (15, datetime(2026, 11, 3), (datetime(2026, 10, 15), datetime(2026, 11, 15))),
        (15, datetime(2026, 11, 15), (datetime(2026, 11, 15), datetime(2026, 12, 15))),
        (31, datetime(2026, 11, 26), (datetime(2026, 10, 31), datetime(2026, 11, 30))),
        (31, datetime(2026, 11, 30), (datetime(2026, 11, 30), datetime(2026, 12, 31))),
        (30, datetime(2027, 2, 28, 1), (datetime(2027, 2, 28), datetime(2027, 3, 30))),
        (10, datetime(2026, 12, 20), (datetime(2026, 12, 10), datetime(2027, 1, 10))),
        (10, datetime(2027, 1, 5), (datetime(2026, 12, 10), datetime(2027, 1, 10))),
    ],
)
def test_credit_cycle_clamps_renewal_day_to_month_length(renews_on, now, expected):
    assert credit_cycle(renews_on, now) == expected


@pytest.mark.parametrize(
    ("model_id", "kind"),
    [
        ("gpt-6.2-astra", "text"),
        ("gpt-5.5", "text"),
        ("o4-mini", "text"),
        ("gpt-image-2.5-sunburst", "image"),
        ("chatgpt-image-latest", "image"),
        ("text-embedding-3-large", None),
        ("gpt-4o-mini-tts", None),
        ("whisper-1", None),
        ("gpt-4o-transcribe", None),
        ("omni-moderation-latest", None),
        ("gpt-realtime", None),
        ("gpt-audio", None),
        ("davinci-002", None),
        ("gpt-3.5-turbo-instruct", None),
        ("sora-2", None),
        ("dall-e-3", None),
    ],
)
def test_model_kind_classifies_conversation_and_image_models(model_id, kind):
    assert model_kind(model_id) == kind


def test_default_names_prefer_registry_then_models_dev_then_id(monkeypatch):
    # models.dev also names gpt-5.5; the native registry's name wins.
    monkeypatch.setattr(pricing_catalog, "_names", {"gpt-5.5": "models.dev GPT-5.5", "gpt-5.5-pro": "GPT-5.5 Pro"})
    state = AccountState(
        catalog=[
            CatalogModel(id=model_id, kind=model_kind(model_id) or "text")
            for model_id in ("gpt-5.5", "gpt-5.5-pro", "gpt-image-2.5-sunburst")
        ],
        selections=[ModelSelection(model="gpt-retired")],
    )
    assert default_model_names(state) == {
        "gpt-5.5": "GPT-5.5",
        "gpt-5.5-pro": "GPT-5.5 Pro",
        "gpt-image-2.5-sunburst": "gpt-image-2.5-sunburst",
        "gpt-retired": "gpt-retired",
    }
