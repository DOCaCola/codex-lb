"""Public native compact -> on-demand owner-pinned handoff -> source paths."""

import asyncio
import json
from copy import deepcopy

import pytest
from aiohttp import web
from sqlalchemy import select

from app.core.clients.proxy import ProxyResponseError
from app.core.clients.proxy_websocket import UpstreamWebSocketMessage
from app.core.errors import openai_error
from app.db.models import Account, ApiKeyUsageReservation, RequestLog
from app.db.session import get_background_session
from app.modules.proxy import service as proxy_service
from tests.integration import test_checkpoint_history_routing as recovery_fixtures
from tests.integration.model_source_helpers import _create_model_source, stub_source_upstreams
from tests.integration.test_checkpoint_history_routing import (
    MODEL,
    PATHS,
    checkpoint,
    history,
    websocket,
)
from tests.integration.test_proxy_affinity_websocket_observation import SyntheticUpstream

pytestmark = pytest.mark.integration
recovery_env = recovery_fixtures.recovery_env
opus_pool = recovery_fixtures.opus_pool


@pytest.fixture
async def handoff_env(recovery_env, monkeypatch):
    headers, compact_calls, captured, closed, directory = recovery_env
    generated, finished = [], []
    outcome = {"status": "completed", "text": "Task handoff: preserve the original decision and critical evidence."}

    async def native_stream(payload, *args, **kwargs):
        generated.append((deepcopy(payload.model_dump(mode="json")), kwargs))
        try:
            if "started" in outcome:
                outcome["started"].set()
                await outcome["finish"].wait()
            response = {
                "id": "resp_handoff",
                "object": "response",
                "status": outcome["status"],
                "model": payload.model,
                "output": [
                    {
                        "type": "message",
                        "id": "msg_handoff",
                        "role": "assistant",
                        "status": "completed",
                        "content": [{"type": "output_text", "text": outcome["text"]}],
                    }
                ],
                "usage": {"input_tokens": 101, "output_tokens": 20, "total_tokens": 121},
            }
            if "error" in outcome:
                status = outcome.get("error_status", 400)
                code = "upstream_error" if status >= 500 else "invalid_encrypted_content"
                raise ProxyResponseError(status, openai_error(code, "Native handoff rejected"))
            if outcome.get("refusal"):
                response["output"][0]["content"].append({"type": "refusal", "refusal": "Cannot summarize"})
            if outcome.get("tool"):
                response["output"].append({"type": "function_call", "call_id": "unexpected", "arguments": "{}"})
            yield "data: " + json.dumps({"type": "response." + outcome["status"], "response": response}) + "\n\n"
        finally:
            finished.append(True)

    monkeypatch.setattr(proxy_service, "core_stream_responses", native_stream)
    return headers, generated, finished, captured, directory, outcome


async def observe_compact(client, headers, directory, *, items=None):
    compact = await client.post(
        "/backend-api/codex/responses/compact",
        headers=headers,
        json={"model": "gpt-5.1", "input": history() if items is None else items, "instructions": "Keep constraints"},
    )
    assert compact.status_code == 200, compact.text
    # The available-snapshot regression fixture explicitly seeds older snapshots.
    # Remove it to exercise provenance-only production behavior.
    for record in directory.glob("*.replay"):
        record.unlink()
    return compact


@pytest.mark.parametrize("path", PATHS)
async def test_http_handoff_only_on_switch_cached_and_metered(async_client, handoff_env, path):
    headers, generated, finished, captured, directory, outcome = handoff_env
    await observe_compact(async_client, headers, directory)
    assert not generated
    visible = [{"role": "user", "content": "A new constraint after compaction"}]
    body = {"model": MODEL, "input": [checkpoint(), *visible], "stream": False}
    for _ in range(2):
        result = await async_client.post(path, headers=headers, json=body)
        assert result.status_code == 200, result.text
    assert len(generated) == len(finished) == 1
    sent, kwargs = generated[0]
    assert sent["model"] == "gpt-5.1"
    assert sent["input"][0] == checkpoint()
    assert len(sent["input"]) == 2 and "A new constraint" not in json.dumps(sent)
    assert sent["tools"] == [] and sent["truncation"] == "disabled" and sent["store"] is False
    for _, _, source_body, _ in captured:
        wire = json.dumps(source_body)
        assert outcome["text"] in wire and "A new constraint" in wire
        assert "PRIVATE" not in wire
    async with get_background_session() as session:
        log = (
            (await session.execute(select(RequestLog).where(RequestLog.archive_request_id.like("handoff_%"))))
            .scalars()
            .all()
        )
        assert len(log) == 1 and log[0].input_tokens == 101 and log[0].output_tokens == 20
        assert log[0].account_id is not None and log[0].model == "gpt-5.1"
    assert not list(directory.glob("*.replay"))
    raw = b"".join(p.read_bytes() for p in (directory / "origins").glob("*.replay"))
    assert b"Original decision" not in raw and b"PRIVATE" not in raw


@pytest.mark.parametrize("path", PATHS)
async def test_websocket_handoff_and_source_continuation(async_client, handoff_env, path):
    headers, generated, finished, captured, directory, outcome = handoff_env
    await observe_compact(async_client, headers, directory)
    async with websocket(async_client._transport.app, path, headers) as turn:
        first = await turn({"model": MODEL, "input": [checkpoint(), {"role": "user", "content": "Continue"}]})
        assert first["type"] == "response.completed", first
        second = await turn(
            {"model": MODEL, "previous_response_id": first["response"]["id"], "input": "Continue again"}
        )
        assert second["type"] == "response.completed", second
    assert len(generated) == len(finished) == 1
    assert outcome["text"] in json.dumps(captured[-1][2])


@pytest.mark.parametrize(
    "outcome_update", [{"status": "incomplete"}, {"text": ""}, {"refusal": True}, {"error": True}, {"tool": True}]
)
async def test_invalid_handoff_never_dispatches_source(async_client, handoff_env, outcome_update):
    headers, generated, finished, captured, directory, outcome = handoff_env
    await observe_compact(async_client, headers, directory)
    outcome.update(outcome_update)
    result = await async_client.post(
        PATHS[1],
        headers=headers,
        json={"model": MODEL, "input": [checkpoint()], "stream": False},
    )
    assert result.status_code >= 400, result.text
    assert len(generated) == len(finished) == 1 and not captured
    assert not list((directory / "handoffs").glob("*.replay"))


async def test_successful_compact_over_old_opaque_input_establishes_provenance(async_client, handoff_env):
    headers, generated, finished, captured, directory, outcome = handoff_env
    await observe_compact(
        async_client,
        headers,
        directory,
        items=[{**checkpoint(), "encrypted_content": "OLDER_OPAQUE"}, *history()],
    )
    result = await async_client.post(
        PATHS[1],
        headers=headers,
        json={"model": MODEL, "input": [checkpoint()], "stream": False},
    )
    assert result.status_code == 200, result.text
    assert len(generated) == 1 and outcome["text"] in json.dumps(captured[0][2])


async def test_paused_owner_is_not_replaced(async_client, handoff_env):
    headers, generated, finished, captured, directory, outcome = handoff_env
    await observe_compact(async_client, headers, directory)
    from tests.integration.test_proxy_compact import _import_account

    await _import_account(async_client, email="backup@example.invalid", raw_account_id="backup-owner")
    async with get_background_session() as session:
        account = (
            (await session.execute(select(Account).where(Account.chatgpt_account_id == "affinity-test-account")))
            .scalars()
            .one()
        )
        account.status = "paused"
        await session.commit()
    from app.modules.proxy.account_cache import get_account_selection_cache

    get_account_selection_cache().invalidate()
    result = await async_client.post(
        PATHS[1],
        headers=headers,
        json={"model": MODEL, "input": [checkpoint()], "stream": False},
    )
    assert result.status_code >= 400, result.text
    assert not generated and not captured


async def test_transient_native_failure_never_sends_checkpoint_to_backup(async_client, handoff_env, monkeypatch):
    from tests.integration.test_proxy_compact import _import_account

    headers, generated, finished, captured, directory, outcome = handoff_env
    await observe_compact(async_client, headers, directory)
    backup = await _import_account(async_client, email="healthy@example.invalid", raw_account_id="healthy-backup")
    monkeypatch.setattr(proxy_service, "_MAX_TRANSIENT_SAME_ACCOUNT_RETRIES", 0)
    outcome.update(error=True, error_status=503)
    async with get_background_session() as session:
        owner = (
            await session.execute(select(Account.id).where(Account.chatgpt_account_id == "affinity-test-account"))
        ).scalar_one()
    response = await async_client.post(
        PATHS[1], headers=headers, json={"model": MODEL, "input": [checkpoint()], "stream": False}
    )
    assert response.status_code >= 400, response.text
    assert generated and len(generated) == len(finished) and not captured
    assert all(
        kwargs["codex_lb_account_id"] == owner and kwargs["codex_lb_account_id"] != backup for _, kwargs in generated
    )


async def test_no_handoff_for_readable_or_portable_context(async_client, handoff_env):
    from app.core.openai.compaction import encode_codex_lb_compaction_summary

    headers, generated, finished, captured, directory, outcome = handoff_env
    for input_items in [
        history(),
        [{"type": "compaction", "encrypted_content": encode_codex_lb_compaction_summary("Portable context")}],
    ]:
        result = await async_client.post(
            PATHS[1], headers=headers, json={"model": MODEL, "input": input_items, "stream": False}
        )
        assert result.status_code == 200, result.text
    assert not generated and len(captured) == 2


@pytest.mark.parametrize("path", PATHS)
async def test_native_websocket_compact_then_handoff(async_client, handoff_env, path):
    headers, generated, finished, captured, directory, outcome = handoff_env
    async with websocket(async_client._transport.app, path, headers) as turn:
        compact = await turn({"model": "gpt-5.1", "input": [*history(), {"type": "compaction_trigger"}]})
        assert compact["type"] == "response.completed", compact
        assert compact["response"]["output"] == [checkpoint()] and not generated
        for record in directory.glob("*.replay"):
            record.unlink()
        switched = await turn({"model": MODEL, "input": [checkpoint(), {"role": "user", "content": "Continue"}]})
        assert switched["type"] == "response.completed", switched
    assert len(generated) == len(finished) == 1
    assert outcome["text"] in json.dumps(captured[0][2])


async def test_native_delta_compact_output_events_establish_provenance(async_client, handoff_env, monkeypatch):
    headers, generated, finished, captured, directory, outcome = handoff_env
    native_requests = []

    class NativeDeltaSocket(SyntheticUpstream):
        async def send_text(self, text):
            request = json.loads(text)
            native_requests.append(request)
            compacting = request.get("previous_response_id") is not None
            response_id = "resp_delta_compact" if compacting else "resp_before_compact"
            events = [{"type": "response.created", "response": {"id": response_id, "status": "in_progress"}}]
            if compacting:
                events.append({"type": "response.output_item.done", "output_index": 0, "item": checkpoint()})
            events.append(
                {
                    "type": "response.completed",
                    "response": {
                        "id": response_id,
                        "object": "response",
                        "model": request["model"],
                        "status": "completed",
                        "output": [],
                        "usage": {"input_tokens": 10, "output_tokens": 10, "total_tokens": 20},
                    },
                }
            )
            for event in events:
                self.messages.put_nowait(UpstreamWebSocketMessage(kind="text", text=json.dumps(event)))

    async def connect(*args, **kwargs):
        return NativeDeltaSocket()

    monkeypatch.setattr(proxy_service, "connect_responses_websocket", connect)
    async with websocket(async_client._transport.app, PATHS[1], headers) as turn:
        first = await turn({"model": "gpt-5.1", "input": "Task before compact"})
        assert first["type"] == "response.completed", first
        compact = await turn(
            {
                "model": "gpt-5.1",
                "previous_response_id": first["response"]["id"],
                "input": [{"type": "compaction_trigger"}],
            }
        )
        assert compact["type"] == "response.completed", compact
        assert native_requests[-1]["previous_response_id"] == "resp_before_compact" and not generated
        switched = await turn({"model": MODEL, "input": [checkpoint(), {"role": "user", "content": "Continue"}]})
        assert switched["type"] == "response.completed", switched
    assert len(generated) == len(finished) == 1
    assert outcome["text"] in json.dumps(captured[0][2])


@pytest.mark.parametrize("path", PATHS)
async def test_source_compaction_handoff(async_client, handoff_env, path):
    headers, generated, finished, captured, directory, outcome = handoff_env
    await observe_compact(async_client, headers, directory)
    response = await async_client.post(
        path + "/compact",
        headers=headers,
        json={
            "model": MODEL,
            "instructions": "Preserve all task state",
            "input": [checkpoint(), {"role": "user", "content": "Latest constraint"}],
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["output"][0]["encrypted_content"].startswith("clb1:")
    assert len(generated) == len(finished) == 1
    assert outcome["text"] in json.dumps(captured[0][2]) and "Latest constraint" in json.dumps(captured[0][2])


async def test_generic_source_handoff(async_client, handoff_env):
    headers, generated, finished, _, directory, outcome = handoff_env
    await observe_compact(async_client, headers, directory)
    captured = []

    async def handler(request):
        captured.append(await request.json())
        return web.json_response(
            {"id": "resp_generic", "object": "response", "status": "completed", "output": [], "usage": {}}
        )

    async with stub_source_upstreams() as start:
        await _create_model_source(
            async_client,
            name="handoff-generic",
            model="generic-model",
            base_url=await start(handler),
            supports_responses=True,
        )
        response = await async_client.post(
            PATHS[0],
            headers=headers,
            json={"model": "generic-model", "input": [checkpoint(), {"role": "user", "content": "Continue"}]},
        )
    assert response.status_code == 200, response.text
    assert len(generated) == len(finished) == len(captured) == 1
    wire = json.dumps(captured[0])
    assert outcome["text"] in wire and "Continue" in wire and "PRIVATE" not in wire


async def test_unknown_or_cross_scope_checkpoint_never_generates(async_client, handoff_env):
    headers, generated, finished, captured, directory, outcome = handoff_env
    await observe_compact(async_client, headers, directory)
    for input_item, request_headers in [
        ({**checkpoint(), "encrypted_content": "UNOBSERVED"}, headers),
        (checkpoint(), {**headers, "session_id": "different-conversation"}),
    ]:
        response = await async_client.post(
            PATHS[1], headers=request_headers, json={"model": MODEL, "input": [input_item], "stream": False}
        )
        assert response.status_code == 400, response.text
        assert response.json()["error"]["code"] == "compaction_history_unavailable"
    assert not generated and not captured


async def test_native_continuation_unchanged(async_client, handoff_env):
    headers, generated, finished, captured, directory, outcome = handoff_env
    await observe_compact(async_client, headers, directory)
    response = await async_client.post(
        PATHS[1], headers=headers, json={"model": "gpt-5.1", "input": [checkpoint()], "stream": False}
    )
    assert response.status_code == 200, response.text
    assert len(generated) == 1 and generated[0][0]["input"] == [checkpoint()]
    assert not captured and not list((directory / "handoffs").glob("*.replay"))


@pytest.mark.parametrize("transport", ["http", "websocket"])
async def test_concurrent_switch_busy_has_retry_after(async_client, handoff_env, transport):
    headers, generated, finished, captured, directory, outcome = handoff_env
    await observe_compact(async_client, headers, directory)
    outcome.update(started=asyncio.Event(), finish=asyncio.Event())
    body = {"model": MODEL, "input": [checkpoint()], "stream": False}
    first = asyncio.create_task(async_client.post(PATHS[1], headers=headers, json=body))
    await asyncio.wait_for(outcome["started"].wait(), 5)
    try:
        if transport == "http":
            second = await async_client.post(PATHS[1], headers=headers, json=body)
            assert second.status_code == 503, second.text
            assert second.json()["error"]["code"] == "compaction_handoff_in_progress"
            assert second.headers["retry-after"] == "2"
        else:
            async with websocket(async_client._transport.app, PATHS[1], headers) as turn:
                event = await turn(body)
                assert event["type"] == "error" and event["status"] == 503, event
                assert event["error"]["code"] == "compaction_handoff_in_progress"
                assert event["headers"]["retry-after"] == "2"
        assert not captured
    finally:
        outcome["finish"].set()
        response = await first
    assert response.status_code == 200, response.text
    assert len(generated) == len(finished) == 1


async def test_cancelled_handoff_closes_native_work_and_releases_claim(async_client, handoff_env):
    headers, generated, finished, captured, directory, outcome = handoff_env
    await observe_compact(async_client, headers, directory)
    key_id = (await async_client.get("/api/api-keys/")).json()[0]["id"]
    configured = await async_client.patch(
        f"/api/api-keys/{key_id}",
        json={"limits": [{"limitType": "total_tokens", "limitWindow": "weekly", "maxValue": 1_000_000}]},
    )
    assert configured.status_code == 200, configured.text
    outcome.update(started=asyncio.Event(), finish=asyncio.Event())
    body = {"model": MODEL, "input": [checkpoint()], "stream": False}
    task = asyncio.create_task(async_client.post(PATHS[1], headers=headers, json=body))
    await asyncio.wait_for(outcome["started"].wait(), 5)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert len(finished) == 1 and not captured
    assert not list((directory / "handoffs").glob("*.replay"))
    # Ordinary native streaming transfers cancelled reservation cleanup to
    # tracked persistence tasks rather than blocking the response on SQLite.
    assert await async_client._transport.app.state.proxy_service.drain_persistence_tasks(timeout_seconds=5)
    async with get_background_session() as session:
        outstanding = (
            (await session.execute(select(ApiKeyUsageReservation).where(ApiKeyUsageReservation.status == "reserved")))
            .scalars()
            .all()
        )
        assert not outstanding
    outcome["finish"].set()
    response = await async_client.post(PATHS[1], headers=headers, json=body)
    assert response.status_code == 200, response.text
    assert len(generated) == len(finished) == 2


@pytest.mark.parametrize("cached", [False, True])
@pytest.mark.parametrize("restriction", ["model", "account"])
async def test_current_key_permissions_block_handoff(async_client, handoff_env, cached, restriction):
    from tests.integration.test_proxy_compact import _import_account

    headers, generated, finished, captured, directory, outcome = handoff_env
    await observe_compact(async_client, headers, directory)
    body = {"model": MODEL, "input": [checkpoint()], "stream": False}
    if cached:
        response = await async_client.post(PATHS[1], headers=headers, json=body)
        assert response.status_code == 200, response.text
    key_id = (await async_client.get("/api/api-keys/")).json()[0]["id"]
    if restriction == "model":
        settings = {"allowedModels": [MODEL]}
    else:
        backup = await _import_account(async_client, email="scope@example.invalid", raw_account_id="scope-owner")
        settings = {"assignedAccountIds": [backup]}
    configured = await async_client.patch(f"/api/api-keys/{key_id}", json=settings)
    assert configured.status_code == 200, configured.text
    initial_generations, initial_dispatches = len(generated), len(captured)
    response = await async_client.post(PATHS[1], headers=headers, json=body)
    assert response.status_code == 403, response.text
    assert len(generated) == initial_generations and len(captured) == initial_dispatches


async def test_destination_enforcement_never_rewrites_native_origin_and_handoff_settles(async_client, handoff_env):
    headers, generated, finished, captured, directory, outcome = handoff_env
    await observe_compact(async_client, headers, directory)
    key_id = (await async_client.get("/api/api-keys/")).json()[0]["id"]
    configured = await async_client.patch(
        f"/api/api-keys/{key_id}",
        json={
            "enforcedModel": MODEL,
            "limits": [{"limitType": "total_tokens", "limitWindow": "weekly", "maxValue": 1_000_000}],
        },
    )
    assert configured.status_code == 200, configured.text
    response = await async_client.post(
        PATHS[1], headers=headers, json={"model": "gpt-5.1", "input": [checkpoint()], "stream": False}
    )
    assert response.status_code == 200, response.text
    assert generated[0][0]["model"] == "gpt-5.1" and captured
    assert await async_client._transport.app.state.proxy_service.drain_persistence_tasks(timeout_seconds=5)
    async with get_background_session() as session:
        reservations = (
            (await session.execute(select(ApiKeyUsageReservation).where(ApiKeyUsageReservation.model == "gpt-5.1")))
            .scalars()
            .all()
        )
        assert len(reservations) == 1 and reservations[0].status == "finalized"
        assert reservations[0].input_tokens == 101 and reservations[0].output_tokens == 20


async def test_handoff_timeout_does_not_dispatch_and_releases_claim(async_client, handoff_env, monkeypatch):
    from app.modules.proxy import api

    headers, generated, finished, captured, directory, outcome = handoff_env
    await observe_compact(async_client, headers, directory)
    outcome.update(started=asyncio.Event(), finish=asyncio.Event())
    monkeypatch.setattr(api, "HANDOFF_TIMEOUT_SECONDS", 0.05)
    body = {"model": MODEL, "input": [checkpoint()], "stream": False}
    response = await async_client.post(PATHS[1], headers=headers, json=body)
    assert response.status_code == 504, response.text
    assert response.json()["error"]["code"] == "compaction_handoff_timeout"
    assert len(generated) == len(finished) == 1 and not captured
    outcome["finish"].set()
    response = await async_client.post(PATHS[1], headers=headers, json=body)
    assert response.status_code == 200, response.text
