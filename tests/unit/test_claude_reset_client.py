import json
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from app.modules.claude import reset_client
from app.modules.claude.reset_client import ClaimUnknown, ResetClient
from app.modules.claude.reset_schemas import GrantStatus

ORG = UUID("f737e84e-fd7d-4d90-8e19-a39f26b333cd")


@pytest.mark.parametrize(
    "http_status,body,expected",
    [
        (200, {"result": "reset", "resets_left": 0, "cleared": ["five_hour"]}, "reset"),
        (401, {}, "auth_error"),
        (403, {}, "auth_error"),
        (429, {}, "rate_limited"),
        (500, {}, None),
        (200, {"result": "unexpected"}, None),
        (200, {"result": "reset", "cleared": ["unknown_window"]}, None),
        (200, {"result": "reset", "resets_left": -1}, None),
    ],
)
async def test_claim_wire_and_unknown_outcomes(monkeypatch, http_status, body, expected):
    calls = []

    async def chunks(_size):
        yield json.dumps(body).encode()

    @asynccontextmanager
    async def post(url, **kwargs):
        calls.append((url, kwargs))
        yield SimpleNamespace(status=http_status, content=SimpleNamespace(iter_chunked=chunks))

    @asynccontextmanager
    async def lease():
        yield SimpleNamespace(post=post)

    monkeypatch.setattr(reset_client, "lease_model_source_session", lease)
    operation_id = str(uuid4())
    if expected is None:
        with pytest.raises(ClaimUnknown):
            await ResetClient().claim("test-only-token", "2.1.280", ORG, "grant", operation_id)
    else:
        answer = await ResetClient().claim("test-only-token", "2.1.280", ORG, "grant", operation_id)
        assert answer.result == expected
    assert len(calls) == 1
    url, options = calls[0]
    assert url.endswith(f"/api/organizations/{ORG}/reset_rate_limits")
    assert options["json"] == {"program": "cedar_ember", "grant_id": "grant", "request_id": operation_id}
    assert options["headers"]["User-Agent"] == "claude-cli/2.1.280 (external, cli)"
    assert options["headers"]["x-app"] == "cli"
    assert options["allow_redirects"] is False


def test_missing_and_malformed_grants_are_not_zero():
    with pytest.raises(ValidationError):
        GrantStatus.model_validate({})
    with pytest.raises(ValidationError):
        GrantStatus.model_validate({"eligible": True, "at_limit": True, "grants": [{"id": "x"}]})
    empty = GrantStatus(eligible=True, at_limit=True, grants=[])
    assert not empty.usable("missing", datetime.now(UTC))
