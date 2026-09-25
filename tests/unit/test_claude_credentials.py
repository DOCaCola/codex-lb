from __future__ import annotations

from datetime import UTC, datetime
from urllib.parse import parse_qs, urlparse

import pytest
from cryptography.fernet import Fernet
from pydantic import ValidationError

from app.core.crypto import TokenEncryptor
from app.modules.claude.credentials import PKCE, ClaudeError, decrypt_credentials, encrypt_credentials
from app.modules.claude.schemas import CredentialFile, TokenResponse


def credential_file(**overrides):
    return {
        "claudeAiOauth": {
            "accessToken": "private-access",
            "refreshToken": "private-refresh",
            "expiresAt": 1_800_000_000_000,
            "scopes": ["user:inference", "user:profile"],
            **overrides,
        }
    }


@pytest.mark.parametrize("expiry", [None, 1_800_000_000, "1800000000000", True, -1, 10**20])
def test_import_rejects_ambiguous_expiry(expiry):
    with pytest.raises(ValidationError) as exc:
        CredentialFile.model_validate(credential_file(expiresAt=expiry))
    assert "private-access" not in str(exc.value)


def test_import_normalizes_milliseconds_and_encrypts_secrets():
    credentials = CredentialFile.model_validate(credential_file()).claudeAiOauth.credentials()
    assert credentials.expires_at == datetime.fromtimestamp(1_800_000_000, UTC)
    assert "private-access" not in repr(credentials)
    assert "private-refresh" not in credentials.model_dump_json()
    encryptor = TokenEncryptor(key=Fernet.generate_key())
    encrypted = encrypt_credentials(credentials, encryptor)
    assert b"private-access" not in encrypted
    assert decrypt_credentials(encrypted, encryptor) == credentials


def test_token_response_uses_seconds_not_milliseconds():
    token = TokenResponse.model_validate(
        {
            "access_token": "a",
            "refresh_token": "r",
            "token_type": "Bearer",
            "expires_in": 3600,
            "scope": "user:inference",
        }
    )
    assert token.credentials(datetime(2026, 1, 1, tzinfo=UTC)).expires_at == datetime(2026, 1, 1, 1, tzinfo=UTC)


def test_pkce_state_and_verifier_are_independent_and_bound():
    flow = PKCE.create()
    second = PKCE.create()
    assert len({flow.state, flow.verifier, second.state, second.verifier}) == 4
    query = parse_qs(urlparse(flow.authorization_url).query)
    assert query["code_challenge_method"] == ["S256"]
    assert query["state"] == [flow.state]
    assert flow.verifier not in flow.authorization_url
    assert flow.exchange_body(f"code#{flow.state}")["code"] == "code"
    with pytest.raises(ClaudeError, match="state"):
        flow.exchange_body(f"code#{second.state}")


def test_import_requires_inference_grant():
    with pytest.raises(ValidationError, match="inference"):
        CredentialFile.model_validate(credential_file(scopes=["user:profile"]))
