from __future__ import annotations

import asyncio
import hashlib
import hmac
import ipaddress
import socket
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit

import aiohttp
from aiohttp.abc import ResolveResult

from app.modules.quota_webhook.repository import ClaimedDelivery


class BlockedDestination(ValueError):
    pass


def validate_url(url: str) -> None:
    try:
        parsed = urlsplit(url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
            raise ValueError
        if parsed.port is not None and not 1 <= parsed.port <= 65535:
            raise ValueError
        if len(url) > 4096 or any(ord(char) < 33 for char in url):
            raise ValueError
        try:
            address = ipaddress.ip_address(parsed.hostname)
        except ValueError:
            address = None
        if address is not None and (not address.is_global or address.is_multicast):
            raise ValueError
    except ValueError as exc:
        raise BlockedDestination("Webhook requires a public HTTPS URL without credentials or fragments") from exc


class PublicResolver(aiohttp.resolver.ThreadedResolver):
    async def resolve(
        self, host: str, port: int = 0, family: socket.AddressFamily = socket.AF_INET
    ) -> list[ResolveResult]:
        addresses = await super().resolve(host, port, family)
        if not addresses or any(
            not ipaddress.ip_address(address["host"]).is_global or ipaddress.ip_address(address["host"]).is_multicast
            for address in addresses
        ):
            raise BlockedDestination("Webhook destination is not public")
        return addresses


@dataclass(frozen=True)
class DeliveryResult:
    status: int | None
    error: str | None
    retryable: bool = False
    retry_after: int = 0


def retry_seconds(value: str | None) -> int:
    if value is None:
        return 0
    try:
        return max(0, min(300, int(value)))
    except ValueError:
        try:
            return max(0, min(300, int((parsedate_to_datetime(value) - datetime.now(UTC)).total_seconds())))
        except (ValueError, TypeError, OverflowError):
            return 0


def signed_headers(delivery: ClaimedDelivery, timestamp: str) -> dict[str, str]:
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "codex-lb-webhook/1",
        "X-Webhook-Id": delivery.event_id,
        "X-Webhook-Timestamp": timestamp,
    }
    if delivery.secret:
        digest = hmac.new(
            delivery.secret.encode(), f"{timestamp}.{delivery.payload}".encode(), hashlib.sha256
        ).hexdigest()
        headers["X-Webhook-Signature"] = "sha256=" + digest
    return headers


async def deliver(delivery: ClaimedDelivery) -> DeliveryResult:
    try:
        validate_url(delivery.url)
        async with aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(resolver=PublicResolver(), use_dns_cache=False),
            timeout=aiohttp.ClientTimeout(total=10),
            trust_env=False,
            cookie_jar=aiohttp.DummyCookieJar(),
        ) as client:
            async with client.post(
                delivery.url,
                data=delivery.payload.encode(),
                headers=signed_headers(delivery, str(int(time.time()))),
                allow_redirects=False,
            ) as response:
                # Never read or log an untrusted response body or URL.
                status = response.status
                if 200 <= status < 300:
                    return DeliveryResult(status, None)
                return DeliveryResult(
                    status,
                    "http_error",
                    status in {408, 429} or status >= 500,
                    retry_seconds(response.headers.get("Retry-After")),
                )
    except BlockedDestination:
        return DeliveryResult(None, "blocked_destination")
    except aiohttp.ClientConnectorCertificateError:
        return DeliveryResult(None, "tls_error")
    except (aiohttp.ClientError, asyncio.TimeoutError):
        return DeliveryResult(None, "transport_error", True)
