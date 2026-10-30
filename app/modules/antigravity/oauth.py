"""Google OAuth for the Antigravity CLI client: PKCE paste flow, refresh and credential import."""

from __future__ import annotations

import base64
import hashlib
import json
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlencode, urlparse

import aiohttp
from pydantic import BaseModel, Field, SecretStr, ValidationError

from app.core.clients.http import lease_model_source_session, read_capped
from app.core.crypto import TokenEncryptor
from app.modules.antigravity.constants import (
    AUTHORIZE_URL,
    CLIENT_ID,
    CLIENT_SECRET,
    GO_SKIP_AUTO_HEADERS,
    REDIRECT_URI,
    SCOPES,
    TOKEN_URL,
    USERINFO_URL,
)
from app.modules.antigravity.errors import AntigravityError, TokenRejected
from app.modules.antigravity.schemas import Credentials, UserInfo

# The CLI's Go HTTP client identifies OAuth and userinfo calls with its default agent.
GO_USER_AGENT = "Go-http-client/1.1"
MAX_AUTH_BYTES = 64 * 1024
# Google answers these OAuth errors when the grant itself is gone; others are transient.
_TERMINAL_GRANT_ERRORS = frozenset({"invalid_grant", "unauthorized_client", "invalid_client"})


class TokenResponse(BaseModel):
    access_token: SecretStr = Field(min_length=1)
    expires_in: int = Field(gt=0)
    refresh_token: SecretStr | None = None


@dataclass(frozen=True)
class PKCE:
    state: str
    verifier: str

    @classmethod
    def create(cls) -> PKCE:
        return cls(state=secrets.token_urlsafe(32), verifier=secrets.token_urlsafe(48))

    @property
    def authorization_url(self) -> str:
        challenge = base64.urlsafe_b64encode(hashlib.sha256(self.verifier.encode()).digest()).rstrip(b"=").decode()
        return (
            AUTHORIZE_URL
            + "?"
            + urlencode(
                {
                    "access_type": "offline",
                    "client_id": CLIENT_ID,
                    "code_challenge": challenge,
                    "code_challenge_method": "S256",
                    "prompt": "consent",
                    "redirect_uri": REDIRECT_URI,
                    "response_type": "code",
                    "scope": " ".join(SCOPES),
                    "state": self.state,
                }
            )
        )


def pasted_code(value: str, state: str) -> str:
    """The authorization code from a pasted callback URL or a bare code, bound to this flow's state."""
    value = value.strip()
    if value.startswith("https://"):
        parsed = urlparse(value)
        if f"{parsed.scheme}://{parsed.netloc}{parsed.path}" != REDIRECT_URI:
            raise AntigravityError("Paste the antigravity.google callback URL or its code")
        query = parse_qs(parsed.query)
        if query.get("state") != [state]:
            raise AntigravityError("OAuth state does not match")
        codes = query.get("code", [])
        if len(codes) != 1:
            raise AntigravityError("The callback URL has no authorization code")
        value = codes[0]
    if not value or any(character.isspace() for character in value):
        raise AntigravityError("OAuth code is required")
    return value


def encrypt_credentials(credentials: Credentials, encryptor: TokenEncryptor) -> bytes:
    return encryptor.encrypt(
        json.dumps(
            {
                "access_token": credentials.access_token.get_secret_value(),
                "refresh_token": credentials.refresh_token.get_secret_value(),
                "expires_at": credentials.expires_at.isoformat(),
            }
        )
    )


def decrypt_credentials(value: bytes, encryptor: TokenEncryptor) -> Credentials:
    return Credentials.model_validate_json(encryptor.decrypt(value))


def imported_refresh_token(document: dict[str, object]) -> str:
    """The refresh token of an agy, OmniRoute or CLIProxyAPI credential file; nothing else is trusted."""
    kind = document.get("type")
    if isinstance(kind, str) and kind not in ("antigravity", "google"):
        raise AntigravityError("The credential file belongs to another provider")
    candidates: list[object] = []
    token = document.get("token")
    if isinstance(token, dict):
        candidates += [token.get("refresh_token"), token.get("refreshToken")]
    candidates += [document.get("refresh_token"), document.get("refreshToken")]
    found = {value.strip() for value in candidates if isinstance(value, str) and value.strip()}
    if len(found) != 1:
        raise AntigravityError(
            "The credential file has no refresh token" if not found else "The credential file has conflicting tokens"
        )
    return found.pop()


async def _bounded(response: aiohttp.ClientResponse) -> bytes:
    body = await read_capped(response, MAX_AUTH_BYTES)
    if len(body) > MAX_AUTH_BYTES:
        raise AntigravityError("Google OAuth response exceeded the size limit", status_code=502)
    return body


async def _token(form: dict[str, str]) -> TokenResponse:
    try:
        async with lease_model_source_session() as session:
            async with session.post(
                TOKEN_URL,
                data=form,
                headers={"User-Agent": GO_USER_AGENT, "Accept-Encoding": "gzip"},
                skip_auto_headers=GO_SKIP_AUTO_HEADERS,
                timeout=aiohttp.ClientTimeout(total=30, connect=10),
                allow_redirects=False,
            ) as response:
                body = await _bounded(response)
                if response.status != 200:
                    try:
                        error = json.loads(body).get("error")
                    except (ValueError, AttributeError):
                        error = None
                    raise TokenRejected(
                        f"Google token endpoint returned HTTP {response.status}",
                        terminal=error in _TERMINAL_GRANT_ERRORS,
                    )
                return TokenResponse.model_validate_json(body)
    except (aiohttp.ClientError, TimeoutError) as exc:
        raise AntigravityError(f"Google token endpoint is unreachable: {type(exc).__name__}", status_code=503) from exc
    except ValidationError as exc:
        raise AntigravityError("Google token endpoint returned an invalid response", status_code=502) from exc


def _credentials(response: TokenResponse, refresh_token: str | None) -> Credentials:
    refresh_value = response.refresh_token.get_secret_value() if response.refresh_token else refresh_token
    if not refresh_value:
        raise AntigravityError("Google did not issue a refresh token; sign in again with consent")
    return Credentials(
        access_token=response.access_token,
        refresh_token=SecretStr(refresh_value),
        expires_at=datetime.now(UTC) + timedelta(seconds=response.expires_in),
    )


async def exchange(flow: PKCE, code: str) -> Credentials:
    response = await _token(
        {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "code_verifier": flow.verifier,
        }
    )
    return _credentials(response, None)


async def refresh(refresh_token: str) -> Credentials:
    """Google refresh tokens do not rotate: the response normally omits one and the grant is kept."""
    response = await _token(
        {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        }
    )
    return _credentials(response, refresh_token)


async def userinfo(access_token: str) -> UserInfo:
    try:
        async with lease_model_source_session() as session:
            async with session.get(
                USERINFO_URL,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "User-Agent": GO_USER_AGENT,
                    "Accept-Encoding": "gzip",
                },
                skip_auto_headers=GO_SKIP_AUTO_HEADERS,
                timeout=aiohttp.ClientTimeout(total=30, connect=10),
                allow_redirects=False,
            ) as response:
                body = await _bounded(response)
                if response.status != 200:
                    raise AntigravityError(f"Google userinfo returned HTTP {response.status}", status_code=502)
                return UserInfo.model_validate_json(body)
    except (aiohttp.ClientError, TimeoutError) as exc:
        raise AntigravityError(f"Google userinfo is unreachable: {type(exc).__name__}", status_code=503) from exc
    except ValidationError as exc:
        raise AntigravityError("Google userinfo returned no account identity", status_code=502) from exc
