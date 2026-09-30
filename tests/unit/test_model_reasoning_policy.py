import pytest

from app.core.model_routing import reasoning_allowed


@pytest.mark.parametrize(
    "allowed,requested,default,expected",
    [
        (None, "future", None, True),
        (["none"], "none", "high", True),
        (["none"], None, "high", False),
        (["high"], None, "high", True),
        (["high"], "none", "high", False),
        (["high"], None, None, False),
        (["high"], "medium", "high", False),
    ],
)
def test_reasoning_policy_preserves_explicit_effort_and_default(allowed, requested, default, expected):
    assert reasoning_allowed(allowed, requested, default) is expected
