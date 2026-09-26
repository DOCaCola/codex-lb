import hashlib
import hmac
import socket
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest

from app.modules.quota_webhook.repository import ClaimedDelivery
from app.modules.quota_webhook.schemas import Observation, detect_reset
from app.modules.quota_webhook.transport import (
    BlockedDestination,
    PublicResolver,
    deliver,
    retry_seconds,
    signed_headers,
    validate_url,
)

pytestmark = pytest.mark.unit
NOW = datetime(2026, 9, 26, 12, tzinfo=UTC)


def observation(percent, *, seconds=0, reset=3600, window=10080):
    return Observation(
        used_percent=percent,
        reset_at=int((NOW + timedelta(seconds=reset)).timestamp()) if reset else None,
        window_minutes=window,
        observed_at=NOW + timedelta(seconds=seconds),
    )


@pytest.mark.parametrize(
    "before,after,expected",
    [
        (observation(90), observation(0, seconds=60), "unexpected"),
        (observation(90), observation(0, seconds=3601, reset=604800), "scheduled"),
        (observation(90), observation(90, seconds=3601), None),
        (observation(90), observation(88, seconds=60), None),
        (observation(90), observation(0, seconds=60, reset=3660), None),
        (observation(90), observation(0, seconds=60, reset=604860), "unexpected"),
        (observation(90, reset=0), observation(0, seconds=60), None),
        (observation(90), observation(0, seconds=-60), None),
        (observation(90), observation(0, seconds=60, window=300), None),
        (observation(90), observation(100, seconds=60), None),
    ],
)
def test_detector(before, after, expected):
    assert detect_reset(before, after) == expected


@pytest.mark.parametrize(
    "url",
    [
        "http://example.com",
        "https://127.0.0.1",
        "https://[::1]",
        "https://10.0.0.1",
        "https://169.254.169.254",
        "https://224.0.0.1",
        "https://user:pass@example.com",
        "https://example.com/#secret",
    ],
)
def test_destination_restrictions(url):
    with pytest.raises(BlockedDestination):
        validate_url(url)


async def test_dns_blocks_private_rebinding(monkeypatch):
    monkeypatch.setattr(
        aiohttp.resolver.ThreadedResolver,
        "resolve",
        AsyncMock(
            return_value=[
                {
                    "hostname": "example.com",
                    "host": "10.0.0.1",
                    "port": 443,
                    "family": socket.AF_INET,
                    "proto": 0,
                    "flags": 0,
                }
            ]
        ),
    )
    with pytest.raises(BlockedDestination):
        await PublicResolver().resolve("example.com", 443)


def test_signing_exact_body_and_retry_budget():
    delivery = ClaimedDelivery("event", "lease", 1, "https://example.com", "secret", '{"a":1}')
    headers = signed_headers(delivery, "123")
    assert headers["X-Webhook-Id"] == "event"
    expected = hmac.new(b"secret", b'123.{"a":1}', hashlib.sha256).hexdigest()
    assert headers["X-Webhook-Signature"] == "sha256=" + expected
    assert retry_seconds("99999") == 300
    assert retry_seconds("garbage") == 0
    assert retry_seconds("-1") == 0


@pytest.mark.parametrize(
    "status,retryable", [(204, False), (302, False), (400, False), (408, True), (429, True), (503, True)]
)
async def test_sender_response_policy_and_isolation(monkeypatch, status, retryable):
    response = MagicMock(status=status, headers={"Retry-After": "12"})
    response.read = AsyncMock(side_effect=AssertionError("must not read receiver body"))
    response_context = MagicMock()
    response_context.__aenter__ = AsyncMock(return_value=response)
    response_context.__aexit__ = AsyncMock(return_value=False)
    client = MagicMock()
    client.post.return_value = response_context
    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=client)
    context.__aexit__ = AsyncMock(return_value=False)
    factory = MagicMock(return_value=context)
    connector = MagicMock()
    monkeypatch.setattr(aiohttp, "ClientSession", factory)
    monkeypatch.setattr(aiohttp, "TCPConnector", connector)
    result = await deliver(ClaimedDelivery("event", "lease", 1, "https://example.com", None, "{}"))
    assert result.status == status and result.retryable is retryable
    assert result.error == (None if status == 204 else "http_error")
    assert factory.call_args.kwargs["trust_env"] is False
    assert isinstance(factory.call_args.kwargs["cookie_jar"], aiohttp.DummyCookieJar)
    assert isinstance(connector.call_args.kwargs["resolver"], PublicResolver)
    assert client.post.call_args.kwargs["allow_redirects"] is False
    response.read.assert_not_called()
