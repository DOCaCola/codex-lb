from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from app.modules.claude import client
from app.modules.claude.client import ClaudeClient
from app.modules.claude.metadata import MetadataHTTPError, refresh_due, retry_deadline
from app.modules.claude.schemas import (
    AccountState,
    HeaderQuotaObservation,
    MetadataRefreshState,
    QuotaWindow,
    UsageSnapshot,
)

pytestmark = pytest.mark.unit
NOW = datetime(2026, 9, 29, 10, tzinfo=UTC)


@pytest.mark.parametrize(
    "value,seconds",
    [
        (None, 300),
        ("invalid", 300),
        ("-1", 300),
        ("1.5", 300),
        ("30", 30),
        (" 120 ", 120),
        ("0", 0),
        ("9" * 500, 300),
        ("Tue, 29 Sep 2026 10:04:00 GMT", 240),
        ("Tue, 29 Sep 2026 09:00:00 GMT", 0),
    ],
)
def test_retry_after(value, seconds):
    assert retry_deadline(value, NOW) == NOW + timedelta(seconds=seconds)


def test_force_skips_own_backoff_but_never_a_rate_limit_or_lease():
    state = AccountState(usage_updated_at=NOW, catalog_updated_at=NOW, subscription_updated_at=NOW)
    assert not refresh_due(state, "catalog", NOW + timedelta(hours=5), force=False, generation=1)
    assert refresh_due(state, "catalog", NOW + timedelta(hours=6), force=False, generation=1)
    assert not refresh_due(state, "subscription", NOW + timedelta(hours=5), force=False, generation=1)
    assert refresh_due(state, "subscription", NOW + timedelta(hours=6), force=False, generation=1)
    assert refresh_due(state, "usage", NOW, force=True, generation=1)
    for refresh in [
        MetadataRefreshState(retry_at=NOW + timedelta(seconds=90), rate_limited_generation=1),
        MetadataRefreshState(operation_id="owner", lease_until=NOW + timedelta(seconds=90)),
    ]:
        state.metadata_refresh["usage"] = refresh
        assert not refresh_due(state, "usage", NOW, force=True, generation=1)
        assert refresh_due(state, "usage", NOW + timedelta(seconds=90), force=True, generation=1)
    state.metadata_refresh["usage"] = MetadataRefreshState(retry_at=NOW + timedelta(seconds=90))
    assert not refresh_due(state, "usage", NOW, force=False, generation=1)
    assert refresh_due(state, "usage", NOW, force=True, generation=1)


def _observed(at: datetime) -> HeaderQuotaObservation:
    return HeaderQuotaObservation(window=QuotaWindow(utilization=10), requested_at=at, observed_at=at)


def test_usage_reads_only_when_header_and_endpoint_evidence_is_idle():
    state = AccountState(usage_updated_at=NOW)
    assert not refresh_due(state, "usage", NOW + timedelta(minutes=14), force=False, generation=1)
    assert refresh_due(state, "usage", NOW + timedelta(minutes=15), force=False, generation=1)
    # Traffic keeps the account fresh: no read while replies carry quota headers.
    state.header_usage = {"five_hour": _observed(NOW + timedelta(minutes=50))}
    assert not refresh_due(state, "usage", NOW + timedelta(minutes=59), force=False, generation=1)
    assert refresh_due(state, "usage", NOW + timedelta(minutes=65), force=False, generation=1)
    # Endpoint-only data still refreshes hourly however busy the account is.
    state.header_usage = {"seven_day": _observed(NOW + timedelta(minutes=59))}
    assert refresh_due(state, "usage", NOW + timedelta(hours=1), force=False, generation=1)
    # The model-scoped window alone does not show general activity.
    state.header_usage = {"seven_day_overage_included": _observed(NOW + timedelta(minutes=14))}
    assert refresh_due(state, "usage", NOW + timedelta(minutes=15), force=False, generation=1)
    assert refresh_due(AccountState(), "usage", NOW, force=False, generation=1)


def test_rate_limit_binds_only_the_credential_generation_that_received_it():
    state = AccountState(
        usage_updated_at=NOW - timedelta(hours=2),
        metadata_refresh={"usage": MetadataRefreshState(retry_at=NOW + timedelta(hours=1), rate_limited_generation=3)},
    )
    assert not refresh_due(state, "usage", NOW, force=False, generation=3)
    assert not refresh_due(state, "usage", NOW, force=True, generation=3)
    assert refresh_due(state, "usage", NOW, force=False, generation=4)
    # A refreshed token still follows the normal cadence.
    state.usage_updated_at = NOW - timedelta(minutes=1)
    assert not refresh_due(state, "usage", NOW, force=False, generation=4)


def test_usage_snapshot_reads_fable_weekly_from_scoped_limits():
    usage = UsageSnapshot.model_validate(
        {
            "limits": [
                {"kind": "weekly_all", "group": "weekly", "scope": None, "percent": 34, "resets_at": None},
                {
                    "kind": "weekly_scoped",
                    "group": "weekly",
                    "scope": {"model": {"id": None, "display_name": "Fable"}, "surface": None},
                    "percent": 12,
                    "resets_at": "2026-11-07T22:00:00+00:00",
                },
            ]
        }
    )
    assert usage.seven_day_overage_included == QuotaWindow(
        utilization=12, resets_at=datetime(2026, 11, 7, 22, tzinfo=UTC)
    )
    other = UsageSnapshot.model_validate(
        {"limits": [{"kind": "weekly_scoped", "scope": {"model": {"display_name": "Opus"}}, "percent": 5}]}
    )
    assert other.seven_day_overage_included is None


@pytest.mark.parametrize(
    "endpoint,path",
    [
        ("usage", "/api/oauth/usage"),
        ("catalog", "/v1/models"),
        ("profile", "/api/oauth/profile"),
        ("bootstrap", "/api/claude_cli/bootstrap"),
    ],
)
async def test_metadata_http_error_preserves_status_deadline_not_body(monkeypatch, endpoint, path):
    calls = []

    @asynccontextmanager
    async def get(url, **kwargs):
        calls.append((url, kwargs))
        # No readable body: rejection must not copy credential-bearing provider content.
        yield SimpleNamespace(status=429, headers={"Retry-After": "600"})

    @asynccontextmanager
    async def lease():
        yield SimpleNamespace(get=get)

    monkeypatch.setattr(client, "lease_model_source_session", lease)
    before = datetime.now(UTC)
    with pytest.raises(MetadataHTTPError) as captured:
        await getattr(ClaudeClient(), endpoint)("test-secret", "2.1.283")
    error = captured.value
    assert error.status == 429
    assert before + timedelta(seconds=600) <= error.retry_at <= datetime.now(UTC) + timedelta(seconds=600)
    assert path in str(error) and "429" in str(error)
    assert "test-secret" not in str(error) and "limit=" not in str(error)
    assert calls[0][1]["allow_redirects"] is False
