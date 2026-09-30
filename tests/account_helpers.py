from types import SimpleNamespace
from typing import Any


def account_fixture(**fields: Any) -> SimpleNamespace:
    """A lightweight account double with the default model-availability contract."""
    return SimpleNamespace(**{"all_models": True, "selected_models": [], **fields})
