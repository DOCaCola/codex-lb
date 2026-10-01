import json
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.modules.claude import client
from app.modules.claude.client import ClaudeClient
from app.modules.claude.credentials import ClaudeError
from app.modules.claude.schemas import CredentialFile, SubscriptionMetadata
from app.modules.claude.subscription import subscription_plan
from tests.unit.test_claude_credentials import credential_file

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "subscription,tier,expected",
    [
        (None, None, "unknown"),
        ("free", None, "free"),
        ("claude_pro", None, "pro"),
        (" MAX ", None, "max"),
        ("max", "default_claude_max_5x", "max_5x"),
        ("max", "default_claude_max_20x", "max_20x"),
        ("pro", "claude_max_20x", "max_20x"),
        ("claude_team", None, "team"),
        (None, "default_claude_enterprise", "enterprise"),
        ("future", "future", "unknown"),
        ("max", "default_claude_max_40x", "max"),
        (None, "default", "unknown"),
        ("not_really_pro", "", "unknown"),
    ],
)
def test_known_identifiers_only(subscription, tier, expected):
    metadata = SubscriptionMetadata(
        subscription_type=subscription,
        rate_limit_tier=tier,
        source="bootstrap",
        observed_at=datetime(2026, 10, 1, tzinfo=UTC),
    )
    assert subscription_plan(metadata) == expected
    assert subscription_plan(None) == "unknown"


def test_import_retains_subscription_but_not_in_rotating_credentials():
    imported = CredentialFile.model_validate(
        credential_file(subscriptionType="max", rateLimitTier="default_claude_max_5x")
    ).claudeAiOauth
    metadata = imported.subscription_metadata()
    assert metadata is not None
    assert metadata.source == "credential_file"
    assert subscription_plan(metadata) == "max_5x"
    assert "subscription" not in imported.credentials().model_dump_json()
    assert CredentialFile.model_validate(credential_file()).claudeAiOauth.subscription_metadata() is None


@pytest.mark.parametrize("malformed", [False, True])
async def test_bootstrap_wire_contract_and_safe_parse_error(monkeypatch, malformed):
    calls = []
    body = {
        "oauth_account": {
            "account_uuid": "account-id",
            "organization_uuid": "org-id",
            "organization_type": "claude_max",
            "organization_rate_limit_tier": "default_claude_max_20x",
            "account_email": "not-returned@example.com",
        }
    }
    if malformed:
        body["oauth_account"]["account_uuid"] = ""

    async def chunks(_size):
        yield json.dumps(body).encode()

    @asynccontextmanager
    async def get(url, **kwargs):
        calls.append((url, kwargs))
        yield SimpleNamespace(status=200, content=SimpleNamespace(iter_chunked=chunks))

    @asynccontextmanager
    async def lease():
        yield SimpleNamespace(get=get)

    monkeypatch.setattr(client, "lease_model_source_session", lease)
    if malformed:
        with pytest.raises(ClaudeError) as captured:
            await ClaudeClient().bootstrap("private-token", "2.1.283")
        assert "private-token" not in str(captured.value)
        assert "not-returned@example.com" not in str(captured.value)
    else:
        result = await ClaudeClient().bootstrap("private-token", "2.1.283")
        assert result.oauth_account.organization_rate_limit_tier == "default_claude_max_20x"
        assert "account_email" not in result.model_dump_json()
    url, options = calls[0]
    assert url == "https://api.anthropic.com/api/claude_cli/bootstrap"
    assert options["headers"]["User-Agent"] == "claude-cli/2.1.283 (external, cli)"
    assert options["headers"]["anthropic-beta"] == "oauth-2025-04-20"
    assert options["headers"]["Authorization"] == "Bearer private-token"
    assert options["allow_redirects"] is False
