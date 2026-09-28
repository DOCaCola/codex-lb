from datetime import UTC, datetime, timedelta

import pytest

from app.modules.claude.failover import classify_refusals
from app.modules.model_sources.forwarding import ModelSourceForwardingError
from tests.claude_quota_helpers import overage_headers

NOW = datetime(2026, 9, 28, tzinfo=UTC)
PREFIX = "anthropic-ratelimit-unified"


def classify(headers, *, detail=None):
    return classify_refusals(
        ModelSourceForwardingError(
            status_code=429,
            upstream_status_code=429,
            payload={"error": detail or {"message": "limited"}},
            upstream_headers=headers,
        ),
        now=NOW,
    )


def test_overage_keeps_deadline_on_model_only():
    result = classify(overage_headers(now=NOW))
    assert [(r.scope, r.until) for r in result] == [("model", NOW + timedelta(hours=80))]


def test_model_window_overshoot_without_status_is_scoped():
    headers = {
        f"{PREFIX}-status": "rejected",
        f"{PREFIX}-5h-status": "allowed",
        f"{PREFIX}-7d-status": "allowed",
        f"{PREFIX}-7d_oi-utilization": "1.02",
        f"{PREFIX}-7d_oi-reset": str((NOW + timedelta(hours=80)).timestamp()),
    }
    result = classify(headers)
    assert [(r.scope, r.until) for r in result] == [("model", NOW + timedelta(hours=80))]


def test_mixed_windows_keep_independent_deadlines():
    result = classify(overage_headers(now=NOW, mixed=True))
    assert [(r.scope, r.until) for r in result] == [
        ("account", NOW + timedelta(hours=2)),
        ("model", NOW + timedelta(hours=80)),
    ]


@pytest.mark.parametrize(
    "raw,healthy",
    [
        ("0", True),
        (".99", True),
        ("1", False),
        ("1.04", False),
        ("NaN", False),
        ("inf", False),
        ("-1", False),
        ("", False),
        ("bad", False),
    ],
)
def test_omitted_window_needs_valid_healthy_usage(raw, healthy):
    headers = overage_headers(now=NOW)
    del headers[f"{PREFIX}-5h-status"]
    headers[f"{PREFIX}-5h-utilization"] = raw
    assert ("account" not in {r.scope for r in classify(headers)}) == healthy


def test_both_missing_statuses_are_not_assumed_healthy():
    headers = overage_headers(now=NOW)
    for window in ("5h", "7d"):
        del headers[f"{PREFIX}-{window}-status"]
        headers[f"{PREFIX}-{window}-utilization"] = "0"
    assert {r.scope for r in classify(headers)} == {"account", "model"}


def test_case_whitespace_and_warning_status():
    headers = {k.upper(): f" {v.upper()} " for k, v in overage_headers(now=NOW).items()}
    headers[f"{PREFIX}-7d-status".upper()] = " ALLOWED_WARNING "
    assert [r.scope for r in classify(headers)] == ["model"]


@pytest.mark.parametrize("mixed", [False, True])
def test_structured_entitlement_without_overage_headers(mixed):
    headers = {f"{PREFIX}-status": "rejected", "retry-after": "120"}
    if mixed:
        headers[f"{PREFIX}-5h-status"] = "rejected"
        headers[f"{PREFIX}-5h-reset"] = str((NOW + timedelta(hours=2)).timestamp())
    result = classify(headers, detail={"details": {"error_code": "credits_required"}, "message": "credits required"})
    assert {r.scope for r in result} == ({"account", "model"} if mixed else {"model"})
    if mixed:
        assert result[0].until == NOW + timedelta(hours=2)


def test_aggregate_deadline_is_not_a_shared_window_deadline():
    headers = overage_headers(now=NOW, mixed=True)
    del headers[f"{PREFIX}-5h-reset"]
    headers[f"{PREFIX}-reset"] = str((NOW + timedelta(hours=80)).timestamp())
    result = classify(headers)
    assert result[0].until == NOW + timedelta(seconds=60)
    assert result[1].until == NOW + timedelta(hours=80)


def test_unknown_mixed_claim_does_not_attribute_retry_after():
    headers = overage_headers(now=NOW, mixed=True)
    del headers[f"{PREFIX}-representative-claim"]
    del headers[f"{PREFIX}-5h-reset"]
    del headers[f"{PREFIX}-7d_oi-reset"]
    assert all(r.until == NOW + timedelta(seconds=60) for r in classify(headers))


def test_model_aggregate_reset_when_specific_reset_missing():
    headers = overage_headers(now=NOW)
    del headers["retry-after"]
    del headers[f"{PREFIX}-7d_oi-reset"]
    headers[f"{PREFIX}-reset"] = str((NOW + timedelta(hours=80)).timestamp())
    assert classify(headers)[0].until == NOW + timedelta(hours=80)


@pytest.mark.parametrize("raw", ["nan", "inf", "1e308", "bad", "-1"])
def test_invalid_model_reset_uses_default(raw):
    headers = overage_headers(now=NOW)
    headers[f"{PREFIX}-7d_oi-reset"] = raw
    del headers["retry-after"]
    assert classify(headers)[0].until == NOW + timedelta(seconds=60)
