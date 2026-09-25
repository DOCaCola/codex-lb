from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import TypeVar

import aiohttp
from pydantic import BaseModel, ValidationError

from app.core.clients.http import lease_model_source_session
from app.modules.claude.credentials import CLIENT_ID, PKCE, TOKEN_URL, ClaudeError
from app.modules.claude.profile import management_headers
from app.modules.claude.schemas import (
    CLAUDE_BASE_URL,
    CatalogModel,
    CatalogPage,
    Credentials,
    TokenResponse,
    UsageSnapshot,
)

T = TypeVar("T", bound=BaseModel)
MAX_METADATA_BYTES = 2 * 1024 * 1024


class TokenRejected(ClaudeError):
    def __init__(self, status: int, *, terminal: bool, retry_seconds: int = 60) -> None:
        super().__init__(f"Claude token endpoint returned HTTP {status}")
        self.terminal = terminal
        self.retry_seconds = retry_seconds


class TokenOutcomeUncertain(ClaudeError):
    pass


async def bounded_body(response: aiohttp.ClientResponse) -> bytes:
    body = bytearray()
    async for chunk in response.content.iter_chunked(65536):
        body.extend(chunk)
        if len(body) > MAX_METADATA_BYTES:
            raise ClaudeError("Claude metadata response exceeded the size limit")
    return bytes(body)


def retry_seconds(value: str | None) -> int:
    if value is not None and value.isdecimal():
        return min(86400, max(1, int(value)))
    return 60


class ClaudeClient:
    async def _token(self, body: dict[str, str]) -> Credentials:
        # Record durable intent in the caller before entering this method. A
        # transport/parse failure cannot prove that a rotating grant survived.
        try:
            async with lease_model_source_session() as session:
                async with session.post(
                    TOKEN_URL,
                    json=body,
                    timeout=aiohttp.ClientTimeout(total=30, connect=10),
                    allow_redirects=False,
                ) as response:
                    raw = await bounded_body(response)
                    if response.status != 200:
                        try:
                            error = json.loads(raw)
                        except (ValueError, UnicodeDecodeError):
                            error = None
                        code = error.get("error") if isinstance(error, dict) else None
                        if isinstance(code, dict):
                            code = code.get("type")
                        terminal = code in ("invalid_grant", "invalid_token")
                        raise TokenRejected(
                            response.status,
                            terminal=terminal,
                            retry_seconds=retry_seconds(response.headers.get("Retry-After")),
                        )
                    return TokenResponse.model_validate_json(raw).credentials(datetime.now(UTC))
        except TokenRejected:
            raise
        except (aiohttp.ClientError, TimeoutError, ValueError) as exc:
            raise TokenOutcomeUncertain("Claude token exchange outcome is uncertain; sign in again") from exc

    async def exchange(self, flow: PKCE, code: str) -> Credentials:
        return await self._token(flow.exchange_body(code))

    async def refresh(self, credentials: Credentials) -> Credentials:
        return await self._token(
            {
                "grant_type": "refresh_token",
                "client_id": CLIENT_ID,
                "refresh_token": credentials.refresh_token.get_secret_value(),
            }
        )

    async def _get(self, path: str, token: str, version: str, schema: type[T]) -> T:
        try:
            async with lease_model_source_session() as session:
                async with session.get(
                    CLAUDE_BASE_URL + path,
                    headers=management_headers(token, version),
                    timeout=aiohttp.ClientTimeout(total=30, connect=10),
                    allow_redirects=False,
                ) as response:
                    if response.status != 200:
                        raise ClaudeError(f"Claude metadata returned HTTP {response.status}")
                    return schema.model_validate_json(await bounded_body(response))
        except (aiohttp.ClientError, TimeoutError, ValidationError) as exc:
            raise ClaudeError("Claude metadata could not be loaded") from exc

    async def catalog(self, token: str, version: str) -> list[CatalogModel]:
        from urllib.parse import urlencode

        models: list[CatalogModel] = []
        cursors: set[str] = set()
        cursor: str | None = None
        for _ in range(100):
            params = {"limit": "100"}
            if cursor is not None:
                params["after_id"] = cursor
            page = await self._get("/v1/models?" + urlencode(params), token, version, CatalogPage)
            models.extend(page.data)
            if not page.has_more:
                if len({model.id for model in models}) != len(models):
                    raise ClaudeError("Claude catalog returned duplicate models")
                return models
            if not page.last_id or page.last_id in cursors:
                raise ClaudeError("Claude catalog pagination did not advance")
            cursors.add(page.last_id)
            cursor = page.last_id
        raise ClaudeError("Claude catalog exceeded the page limit")

    async def usage(self, token: str, version: str) -> UsageSnapshot:
        return await self._get("/api/oauth/usage", token, version, UsageSnapshot)
