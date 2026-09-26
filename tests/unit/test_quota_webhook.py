import hashlib
import hmac
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest

from app.modules.quota_webhook.repository import ClaimedDelivery
from app.modules.quota_webhook.schemas import Observation, detect_reset
from app.modules.quota_webhook.transport import (
    InvalidDestination,
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
        "ftp://example.com",
        "file:///etc/hosts",
        "http://",
        "http://example.com:99999",
        "https://user:pass@example.com",
        "https://example.com/#secret",
    ],
)
def test_destination_restrictions(url):
    with pytest.raises(InvalidDestination):
        validate_url(url)


@pytest.mark.parametrize(
    "url",
    [
        "http://example.com",
        "http://10.9.8.19/hook",
        "https://127.0.0.1/hook",
        "http://[::1]/hook",
        "http://homeautomation.localdomain.name/hook",
    ],
)
def test_internal_and_http_destinations_allowed(url):
    validate_url(url)


async def test_deliver_to_local_http_receiver():
    from aiohttp import web

    requests = []

    async def receive(request):
        requests.append((request.method, await request.json(), request.headers["X-Webhook-Id"]))
        return web.Response(status=204)

    app = web.Application()
    app.router.add_post("/hook", receive)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    try:
        port = runner.addresses[0][1]
        result = await deliver(
            ClaimedDelivery("local-event", "lease", 1, f"http://localhost:{port}/hook", None, '{"type":"quota.test"}')
        )
        assert result.status == 204 and result.error is None
        assert requests == [("POST", {"type": "quota.test"}, "local-event")]
    finally:
        await runner.cleanup()


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
    monkeypatch.setattr(aiohttp, "ClientSession", factory)
    result = await deliver(ClaimedDelivery("event", "lease", 1, "https://example.com", None, "{}"))
    assert result.status == status and result.retryable is retryable
    assert result.error == (None if status == 204 else "http_error")
    assert factory.call_args.kwargs["trust_env"] is False
    assert isinstance(factory.call_args.kwargs["cookie_jar"], aiohttp.DummyCookieJar)
    assert client.post.call_args.kwargs["allow_redirects"] is False
    response.read.assert_not_called()
