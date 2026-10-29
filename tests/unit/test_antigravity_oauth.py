from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import pytest

from app.modules.antigravity.constants import CLIENT_ID, REDIRECT_URI
from app.modules.antigravity.errors import AntigravityError
from app.modules.antigravity.oauth import PKCE, imported_refresh_token, pasted_code


def test_authorization_url_is_the_cli_remote_flow() -> None:
    flow = PKCE(state="s" * 43, verifier="v" * 64)
    query = parse_qs(urlparse(flow.authorization_url).query)
    assert query["client_id"] == [CLIENT_ID]
    assert query["redirect_uri"] == [REDIRECT_URI]
    assert query["code_challenge_method"] == ["S256"]
    assert query["access_type"] == ["offline"]
    assert query["state"] == ["s" * 43]


def test_pasted_callback_url_is_bound_to_state() -> None:
    url = REDIRECT_URI + "?state=abc&code=4/0Ab-code"
    assert pasted_code(url, "abc") == "4/0Ab-code"
    assert pasted_code("  4/0Ab-code  ", "abc") == "4/0Ab-code"
    with pytest.raises(AntigravityError, match="state"):
        pasted_code(url, "other")
    with pytest.raises(AntigravityError, match="callback URL"):
        pasted_code("https://example.com/oauth-callback?state=abc&code=x", "abc")
    with pytest.raises(AntigravityError, match="no authorization code"):
        pasted_code(REDIRECT_URI + "?state=abc", "abc")
    with pytest.raises(AntigravityError, match="required"):
        pasted_code("two words", "abc")


@pytest.mark.parametrize(
    "document",
    [
        {"type": "antigravity", "refresh_token": "1//r"},
        {"token": {"refreshToken": "1//r"}},
        {"type": "google", "token": {"refresh_token": "1//r"}, "refresh_token": "1//r"},
    ],
)
def test_imported_refresh_token_shapes(document: dict[str, object]) -> None:
    assert imported_refresh_token(document) == "1//r"


@pytest.mark.parametrize(
    ("document", "message"),
    [
        ({"type": "claude", "refresh_token": "1//r"}, "another provider"),
        ({"access_token": "ya29"}, "no refresh token"),
        ({"refresh_token": "a", "token": {"refresh_token": "b"}}, "conflicting"),
    ],
)
def test_imported_refresh_token_rejections(document: dict[str, object], message: str) -> None:
    with pytest.raises(AntigravityError, match=message):
        imported_refresh_token(document)
