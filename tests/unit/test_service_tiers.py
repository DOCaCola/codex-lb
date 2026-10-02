from __future__ import annotations

import pytest

from app.core.usage.service_tiers import billable_service_tier


@pytest.mark.parametrize(
    ("requested", "observed", "billable"),
    [
        ("priority", "default", "priority"),
        ("priority", "auto", "priority"),
        ("ultrafast", "default", "ultrafast"),
        ("priority", "flex", "flex"),
        ("ultrafast", "priority", "priority"),
        ("default", "priority", "default"),
        ("flex", "default", "flex"),
        ("priority", "unknown-tier", "priority"),
        ("priority", None, "priority"),
        (None, None, None),
        (None, "default", "default"),
        (None, "auto", "auto"),
        (None, "flex", "flex"),
        (None, "priority", None),
    ],
)
def test_billable_service_tier_only_accepts_proven_downgrades(requested, observed, billable):
    assert billable_service_tier(requested, observed) == billable
