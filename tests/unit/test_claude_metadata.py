from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from app.modules.claude import client
from app.modules.claude.client import ClaudeClient
from app.modules.claude.metadata import MetadataHTTPError, refresh_due, retry_deadline
from app.modules.claude.schemas import AccountState, MetadataRefreshState

pytestmark = pytest.mark.unit
NOW = datetime(2026, 9, 29, 10, tzinfo=UTC)


@pytest.mark.parametrize(
    "value,seconds",
    [
        (None, 180),
        ("invalid", 180),
        ("-1", 180),
        ("1.5", 180),
        ("30", 30),
        (" 120 ", 120),
        ("0", 0),
        ("9" * 500, 180),
        ("Tue, 29 Sep 2026 10:04:00 GMT", 240),
        ("Tue, 29 Sep 2026 09:00:00 GMT", 0),
    ],
)
def test_retry_after(value, seconds):
    assert retry_deadline(value, NOW) == NOW + timedelta(seconds=seconds)


def test_cadence_and_force_never_override_cooldown_or_lease():
    state = AccountState(usage_updated_at=NOW, catalog_updated_at=NOW)
    assert not refresh_due(state, "usage", NOW + timedelta(seconds=179), force=False)
    assert refresh_due(state, "usage", NOW + timedelta(seconds=180), force=False)
    assert not refresh_due(state, "catalog", NOW + timedelta(hours=5), force=False)
    assert refresh_due(state, "catalog", NOW + timedelta(hours=6), force=False)
    assert refresh_due(state, "usage", NOW, force=True)
    for refresh in [
        MetadataRefreshState(retry_at=NOW + timedelta(seconds=90)),
        MetadataRefreshState(operation_id="owner", lease_until=NOW + timedelta(seconds=90)),
    ]:
        state.metadata_refresh["usage"] = refresh
        assert not refresh_due(state, "usage", NOW, force=True)
        assert refresh_due(state, "usage", NOW + timedelta(seconds=90), force=True)


@pytest.mark.parametrize(
    "endpoint,path",
    [
        ("usage", "/api/oauth/usage"),
        ("catalog", "/v1/models"),
        ("profile", "/api/oauth/profile"),
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
