import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from app.core.crypto import TokenEncryptor
from app.db.models import ClaudeAccount
from app.db.session import SessionLocal
from app.modules.claude.auth import ClaudeAuth
from app.modules.claude.client import ClaudeClient, TokenOutcomeUncertain, TokenRejected
from app.modules.claude.credentials import ClaudeError, decrypt_credentials
from app.modules.claude.repository import ClaudeRepository
from app.modules.model_sources.forwarding import ModelSourceForwardingError
from tests.integration.test_claude_inference import MODEL, install_upstream
from tests.integration.test_claude_routing import pool as pool

pytestmark = pytest.mark.integration


def rotated(credentials):
    return credentials.model_copy(
        update={
            "access_token": type(credentials.access_token)("new-" + credentials.access_token.get_secret_value()),
            "refresh_token": type(credentials.refresh_token)("new-" + credentials.refresh_token.get_secret_value()),
            "expires_at": datetime.now(UTC) + timedelta(hours=1),
        }
    )


def unauthorized(status=401, error_type="authentication_error"):
    return ModelSourceForwardingError(
        status_code=status,
        upstream_status_code=status,
        payload={"error": {"type": error_type, "message": "credential rejected"}},
    )


@pytest.mark.parametrize("path", ["/v1/messages", "/v1/responses", "/backend-api/codex/responses"])
async def test_future_expiry_401_refreshes_same_account(async_client, pool, monkeypatch, path):
    from app.modules.claude import transport

    captured, _ = install_upstream(monkeypatch)
    original = transport._open_source_stream
    sent = []
    refresh = AsyncMock(side_effect=rotated)
    monkeypatch.setattr(ClaudeClient, "refresh", refresh)

    async def send(source, *args, **kwargs):
        sent.append((source.id, kwargs["prepared_headers"]["authorization"]))
        if len(sent) == 1:
            raise unauthorized()
        async with SessionLocal() as session:
            row = await session.get(ClaudeAccount, source.id)
            assert row.generation == 2 and row.refresh_intent is None
            assert (
                kwargs["prepared_headers"]["authorization"]
                == "Bearer "
                + decrypt_credentials(row.credentials_encrypted, TokenEncryptor()).access_token.get_secret_value()
            )
        return await original(source, *args, **kwargs)

    monkeypatch.setattr(transport, "_open_source_stream", send)
    configured = await async_client.patch(
        f"/api/claude-accounts/{pool[0]}",
        json={
            "routingPolicy": "burn_first",
            "reasoningRestrictions": {MODEL.removeprefix("anthropic/"): ["medium"]},
        },
    )
    assert configured.status_code == 200, configured.text
    body = {"model": MODEL, "stream": True}
    body.update(
        {"max_tokens": 100, "messages": [{"role": "user", "content": "Hi"}]}
        if path.endswith("messages")
        else {"input": "Hi"}
    )
    if path.endswith("messages"):
        body.update(thinking={"type": "adaptive"}, output_config={"effort": "medium"})
    else:
        body["reasoning"] = {"effort": "medium"}
    result = await async_client.post(path, json=body)
    assert result.status_code == 200, result.text
    assert len(sent) == 2 and sent[0][0] == sent[1][0] and sent[0][1] != sent[1][1]
    assert sent[0][0] == pool[0]
    assert len(captured) == 1
    refresh.assert_awaited_once()


async def test_stale_401_reuses_new_generation_and_cannot_backoff_it(pool):
    client = ClaudeClient()
    client.refresh = AsyncMock(side_effect=rotated)
    async with SessionLocal() as session:
        auth = ClaudeAuth(ClaudeRepository(session), client, TokenEncryptor())
        initial = await auth.snapshot(pool[0])
        fresh = await auth.snapshot(pool[0], rejected_generation=initial.generation)
    async with SessionLocal() as session:
        repository = ClaudeRepository(session)
        reused = await ClaudeAuth(repository, client, TokenEncryptor()).snapshot(
            pool[0], rejected_generation=initial.generation
        )
        assert reused == fresh
        await repository.backoff_rejected_generation(
            pool[0], initial.generation, datetime.now(UTC).replace(tzinfo=None)
        )
        assert (await repository.get(pool[0])).retry_at is None
    client.refresh.assert_awaited_once()


async def test_concurrent_401_cannot_exchange_same_grant_twice(pool):
    started, release = asyncio.Event(), asyncio.Event()
    client = ClaudeClient()

    async def refresh(credentials):
        started.set()
        await release.wait()
        return rotated(credentials)

    client.refresh = AsyncMock(side_effect=refresh)

    async def recover():
        async with SessionLocal() as session:
            return await ClaudeAuth(ClaudeRepository(session), client, TokenEncryptor()).snapshot(
                pool[0], rejected_generation=1
            )

    task = asyncio.create_task(recover())
    try:
        await asyncio.wait_for(started.wait(), 5)
        with pytest.raises(ClaudeError):
            await recover()
    finally:
        release.set()
        await task
    client.refresh.assert_awaited_once()


@pytest.mark.parametrize(
    "failure,status",
    [
        (TokenRejected(400, terminal=True), "reauth_required"),
        (TokenOutcomeUncertain("unknown"), "uncertain"),
    ],
)
async def test_failed_refresh_can_use_portable_alternative(async_client, pool, monkeypatch, failure, status):
    from app.modules.claude import transport

    captured, _ = install_upstream(monkeypatch)
    original = transport._open_source_stream
    failed = []

    async def send(source, *args, **kwargs):
        if not failed:
            failed.append(source.id)
            raise unauthorized()
        assert source.id != failed[0]
        return await original(source, *args, **kwargs)

    refresh = AsyncMock(side_effect=failure)
    monkeypatch.setattr(ClaudeClient, "refresh", refresh)
    monkeypatch.setattr(transport, "_open_source_stream", send)
    response = await async_client.post("/v1/responses", json={"model": MODEL, "input": "Hi", "stream": False})
    assert response.status_code == 200, response.text
    refresh.assert_awaited_once()
    async with SessionLocal() as session:
        row = await session.get(ClaudeAccount, failed[0])
        assert row.credential_status == status
        assert (row.refresh_intent is not None) == (status == "uncertain")


async def test_repeated_401_is_bounded_and_not_revocation(async_client, pool, monkeypatch):
    from app.modules.claude import transport

    sent = []

    async def send(source, *args, **kwargs):
        sent.append(source.id)
        raise unauthorized()

    refresh = AsyncMock(side_effect=rotated)
    monkeypatch.setattr(ClaudeClient, "refresh", refresh)
    monkeypatch.setattr(transport, "_open_source_stream", send)
    response = await async_client.post("/v1/responses", json={"model": MODEL, "input": "Hi", "stream": True})
    assert response.status_code == 401, response.text
    assert len(sent) == 4 and sent[0] == sent[1] and sent[2] == sent[3] and sent[0] != sent[2]
    assert refresh.await_count == 2
    async with SessionLocal() as session:
        for source_id in pool:
            row = await session.get(ClaudeAccount, source_id)
            assert row.credential_status == "ready" and row.retry_at is not None


@pytest.mark.parametrize("status,error_type", [(403, "authentication_error"), (401, "invalid_request_error")])
async def test_non_auth_refusal_does_not_refresh(async_client, pool, monkeypatch, status, error_type):
    from app.modules.claude import transport

    refresh = AsyncMock()
    monkeypatch.setattr(ClaudeClient, "refresh", refresh)
    monkeypatch.setattr(transport, "_open_source_stream", AsyncMock(side_effect=unauthorized(status, error_type)))
    response = await async_client.post("/v1/responses", json={"model": MODEL, "input": "Hi", "stream": True})
    assert response.status_code == status
    refresh.assert_not_awaited()


async def test_canceled_forced_refresh_retains_intent(pool):
    entered = asyncio.Event()
    client = ClaudeClient()

    async def refresh(credentials):
        entered.set()
        await asyncio.Event().wait()

    client.refresh = AsyncMock(side_effect=refresh)

    async def recover():
        async with SessionLocal() as session:
            await ClaudeAuth(ClaudeRepository(session), client, TokenEncryptor()).snapshot(
                pool[0], rejected_generation=1
            )

    task = asyncio.create_task(recover())
    try:
        await asyncio.wait_for(entered.wait(), 5)
    finally:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    with pytest.raises(ClaudeError):
        await recover()
    client.refresh.assert_awaited_once()
    async with SessionLocal() as session:
        row = await session.get(ClaudeAccount, pool[0])
        assert row.refresh_intent is not None and row.generation == 1
