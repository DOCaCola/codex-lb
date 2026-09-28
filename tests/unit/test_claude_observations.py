from datetime import UTC, datetime, timedelta

import pytest

from app.modules.claude.observations import parse_headers
from app.modules.claude.quota import quota_status
from app.modules.claude.schemas import AccountState, QuotaWindow, UsageSnapshot

NOW = datetime(2026, 9, 28, 12, tzinfo=UTC)


@pytest.mark.parametrize(
    "raw,percent",
    [
        ("0", 0),
        (".74", 74),
        ("1", 100),
        ("1.02", 102),
        ("1.04", 104),
        ("42", 4200),
        ("1e308", None),
        ("NaN", None),
        ("inf", None),
        ("-1", None),
        ("", None),
        ("invalid", None),
    ],
)
def test_header_scale(raw, percent):
    result = parse_headers({"Anthropic-Ratelimit-Unified-5h-Utilization": raw}, requested_at=NOW, observed_at=NOW)
    assert (result["five_hour"].window.utilization if result else None) == percent


def test_partial_headers_keep_per_window_freshness():
    state = AccountState(
        usage=UsageSnapshot(five_hour=QuotaWindow(utilization=90), seven_day_opus=QuotaWindow(utilization=45)),
        usage_updated_at=NOW - timedelta(minutes=10),
        usage_error="poll unavailable",
        header_usage=parse_headers(
            {"anthropic-ratelimit-unified-5h-utilization": ".2"}, requested_at=NOW, observed_at=NOW
        ),
    )
    windows = {item.name: item for item in quota_status(state, now=NOW).windows}
    assert windows["five_hour"].utilization == 20
    assert windows["five_hour"].freshness == "fresh"
    assert windows["five_hour"].provenance == "inference_header"
    assert windows["seven_day_opus"].utilization == 45
    assert windows["seven_day_opus"].freshness == "stale"
    assert state.usage_error == "poll unavailable"


def test_expired_header_does_not_restore_older_poll():
    headers = {
        "anthropic-ratelimit-unified-5h-utilization": "1",
        "anthropic-ratelimit-unified-5h-reset": str(NOW.timestamp()),
    }
    state = AccountState(
        usage=UsageSnapshot(five_hour=QuotaWindow(utilization=100)),
        usage_updated_at=NOW - timedelta(minutes=1),
        header_usage=parse_headers(headers, requested_at=NOW, observed_at=NOW),
    )
    window = quota_status(state, now=NOW).windows[0]
    assert window.freshness == "unknown" and not window.exhausted
    assert parse_headers({"anthropic-ratelimit-unified-5h-reset": "123"}, requested_at=NOW, observed_at=NOW) == {}


def test_request_start_orders_poll_and_header_not_completion():
    state = AccountState(
        usage=UsageSnapshot(five_hour=QuotaWindow(utilization=80)),
        usage_requested_at=NOW - timedelta(seconds=10),
        usage_updated_at=NOW + timedelta(seconds=10),
        header_usage=parse_headers(
            {"anthropic-ratelimit-unified-5h-utilization": ".2"}, requested_at=NOW, observed_at=NOW
        ),
    )
    assert quota_status(state, now=NOW).windows[0].utilization == 20
    state.usage_requested_at = NOW + timedelta(seconds=1)
    assert quota_status(state, now=NOW).windows[0].utilization == 80


@pytest.mark.parametrize("reset", ["NaN", "inf", "-1", "0", "1e308", "invalid"])
def test_invalid_reset_does_not_discard_usage_or_invent_deadline(reset):
    result = parse_headers(
        {
            "anthropic-ratelimit-unified-7d-utilization": "1.04",
            "anthropic-ratelimit-unified-7d-reset": reset,
        },
        requested_at=NOW,
        observed_at=NOW,
    )
    assert result["seven_day"].window.utilization == 104
    assert result["seven_day"].window.resets_at is None
