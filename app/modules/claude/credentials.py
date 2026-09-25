from __future__ import annotations

import base64
import hashlib
import json
import secrets
from dataclasses import dataclass
from urllib.parse import urlencode

from app.core.crypto import TokenEncryptor
from app.modules.claude.schemas import Credentials

CLIENT_ID = "9d1c250a-e61b-44d9-88ed-5944d1962f5e"
AUTHORIZE_URL = "https://claude.com/cai/oauth/authorize"
TOKEN_URL = "https://platform.claude.com/v1/oauth/token"
REDIRECT_URI = "https://platform.claude.com/oauth/code/callback"
SCOPES = "user:profile user:inference user:sessions:claude_code user:mcp_servers user:file_upload"


class ClaudeError(ValueError):
    """Public diagnostic; never contains tokens or raw upstream auth bodies."""

    code = "claude_invalid_request"
    status_code = 400


@dataclass(frozen=True)
class PKCE:
    state: str
    verifier: str

    @classmethod
    def create(cls) -> PKCE:
        return cls(state=secrets.token_urlsafe(32), verifier=secrets.token_urlsafe(32))

    @property
    def authorization_url(self) -> str:
        challenge = base64.urlsafe_b64encode(hashlib.sha256(self.verifier.encode()).digest()).rstrip(b"=").decode()
        return (
            AUTHORIZE_URL
            + "?"
            + urlencode(
                {
                    "code": "true",
                    "client_id": CLIENT_ID,
                    "response_type": "code",
                    "redirect_uri": REDIRECT_URI,
                    "scope": SCOPES,
                    "code_challenge": challenge,
                    "code_challenge_method": "S256",
                    "state": self.state,
                }
            )
        )

    def exchange_body(self, code: str) -> dict[str, str]:
        # The hosted callback displays code#state; accept that exact form or a
        # separately supplied code, never an arbitrary callback URL.
        supplied_code, separator, supplied_state = code.strip().partition("#")
        if separator and not secrets.compare_digest(supplied_state, self.state):
            raise ClaudeError("OAuth state does not match")
        if not supplied_code:
            raise ClaudeError("OAuth code is required")
        return {
            "grant_type": "authorization_code",
            "code": supplied_code,
            "state": self.state,
            "client_id": CLIENT_ID,
            "redirect_uri": REDIRECT_URI,
            "code_verifier": self.verifier,
        }


def encrypt_credentials(credentials: Credentials, encryptor: TokenEncryptor) -> bytes:
    value = credentials.model_dump(mode="json", exclude={"access_token", "refresh_token"})
    value["access_token"] = credentials.access_token.get_secret_value()
    value["refresh_token"] = credentials.refresh_token.get_secret_value()
    return encryptor.encrypt(json.dumps(value))


def decrypt_credentials(value: bytes, encryptor: TokenEncryptor) -> Credentials:
    return Credentials.model_validate_json(encryptor.decrypt(value))
