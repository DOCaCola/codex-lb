import asyncio
import json
import os
import threading
from dataclasses import replace
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.core.clients.proxy import ProxyResponseError
from app.core.openai.models import CompactResponsePayload
from app.core.openai.requests import ResponsesCompactRequest
from app.modules.api_keys.service import ApiKeyData
from app.modules.proxy import checkpoint_handoff as handoff
from app.modules.proxy.checkpoint_history import CheckpointHistory, retain_native_checkpoint
from app.modules.proxy.replay_store import ApiKeyScope, HTTPFallbackReplayStore
from tests.simulation.virtual_time import VirtualClock

pytestmark = pytest.mark.unit


def api_key():
    return ApiKeyData(
        id="key",
        name="synthetic",
        key_prefix="synthetic",
        allowed_models=None,
        enforced_model=None,
        enforced_reasoning_effort=None,
        enforced_service_tier=None,
        expires_at=None,
        is_active=True,
        created_at=datetime.now(UTC),
        last_used_at=None,
    )


def checkpoint(token="PRIVATE_NATIVE"):
    return {"type": "compaction", "id": "cmp_original", "encrypted_content": token}


def result(text="Portable task state"):
    return {
        "status": "completed",
        "output": [{"type": "message", "status": "completed", "content": [{"type": "output_text", "text": text}]}],
    }


@pytest.fixture
async def env(monkeypatch, tmp_path):
    origins = HTTPFallbackReplayStore(tmp_path / "origins")
    summaries = HTTPFallbackReplayStore(tmp_path / "summaries")
    monkeypatch.setattr(handoff, "origin_store", lambda: origins)
    monkeypatch.setattr(handoff, "handoff_store", lambda: summaries)
    scope = ApiKeyScope("key")
    await handoff.remember_checkpoint_origin(scope, "gpt-5.1", "owner", checkpoint())
    calls = []

    async def generate(origin, item):
        calls.append((origin, item))
        return result()

    return scope, origins, summaries, calls, generate


async def test_provenance_capture_over_opaque_history_never_copies_input(monkeypatch, tmp_path):
    origins = HTTPFallbackReplayStore(tmp_path / "origins")
    monkeypatch.setattr(handoff, "origin_store", lambda: origins)
    request = ResponsesCompactRequest(
        model="gpt-5.1",
        instructions="PRIVATE_INSTRUCTIONS",
        input=[checkpoint("OLDER_PRIVATE"), {"role": "user", "content": "PRIVATE_IMAGE_AND_HISTORY"}],
    )
    response = CompactResponsePayload.model_validate({"object": "response.compaction", "output": [checkpoint()]})
    await retain_native_checkpoint(request, response, api_key(), "owner")
    cached = await origins.load(ApiKeyScope("key"), handoff.checkpoint_digest("PRIVATE_NATIVE"))
    assert cached.model == "gpt-5.1" and cached.account_id == "owner" and cached.input == []
    raw = b"".join(p.read_bytes() for p in origins.directory.glob("*.replay"))
    assert b"PRIVATE" not in raw and b"encrypted_content" not in raw
    assert sum(p.stat().st_size for p in origins.directory.glob("*.replay")) < 1024
    await retain_native_checkpoint(request, response.model_copy(update={"status": "failed"}), api_key(), "other-owner")
    cached = await origins.load(ApiKeyScope("key"), handoff.checkpoint_digest("PRIVATE_NATIVE"))
    assert cached.account_id == "owner"


async def test_restart_cache_and_scope_isolation(env, monkeypatch):
    scope, origins, summaries, calls, generate = env
    resolver = handoff.CheckpointHandoff(api_key(), generate)
    first = await resolver.resolve(scope, checkpoint())
    assert "Portable task state" in json.dumps(first)
    monkeypatch.setattr(handoff, "handoff_store", lambda: HTTPFallbackReplayStore(summaries.directory))
    assert await handoff.CheckpointHandoff(api_key(), generate).resolve(scope, checkpoint()) == first
    assert await resolver.resolve(ApiKeyScope("other"), checkpoint()) is None
    assert len(calls) == 1 and calls[0][0].account_id == "owner" and calls[0][1] == checkpoint()


async def test_materialization_preserves_tail_and_original_index(env, tmp_path):
    scope, origins, summaries, calls, generate = env
    resolver = handoff.CheckpointHandoff(api_key(), generate)
    service = CheckpointHistory(HTTPFallbackReplayStore(tmp_path / "old-snapshots"), scope)
    tail = [
        {"type": "function_call", "name": "read", "call_id": "call_tail", "arguments": "{}"},
        {"type": "function_call_output", "call_id": "call_tail", "output": "Important evidence"},
        {"role": "user", "content": [{"type": "input_image", "image_url": "data:image/png;base64,AA=="}]},
    ]
    payload = {"input": [checkpoint(), *tail]}
    restored = await service.materialize(payload, resolver.resolve)
    assert restored["input"][1:] == tail and payload["input"][0] == checkpoint()
    from app.core.openai.exceptions import ClientPayloadError

    with pytest.raises(ClientPayloadError) as error:
        await service.materialize({"input": [checkpoint(), checkpoint("unobserved")]}, resolver.resolve)
    assert error.value.param == "input[1]"


async def test_cross_worker_claim_prevents_duplicate_generation(env):
    scope, origins, summaries, calls, _ = env
    started, finish = asyncio.Event(), asyncio.Event()

    async def generate(origin, item):
        calls.append(origin)
        started.set()
        await finish.wait()
        return result()

    first = asyncio.create_task(handoff.CheckpointHandoff(api_key(), generate).resolve(scope, checkpoint()))
    await started.wait()
    try:
        with pytest.raises(ProxyResponseError) as error:
            await handoff.CheckpointHandoff(api_key(), generate).resolve(scope, checkpoint())
        assert error.value.status_code == 503 and "in_progress" in json.dumps(error.value.payload)
    finally:
        finish.set()
        await first
    assert len(calls) == 1


@pytest.mark.parametrize("failure", ["error", "cancel"])
async def test_generation_failure_releases_claim(env, failure):
    scope, origins, summaries, calls, generate = env

    async def fail(origin, item):
        if failure == "cancel":
            raise asyncio.CancelledError()
        raise ProxyResponseError(503, {"error": {"message": "Unavailable"}})

    with pytest.raises(asyncio.CancelledError if failure == "cancel" else ProxyResponseError):
        await handoff.CheckpointHandoff(api_key(), fail).resolve(scope, checkpoint())
    assert not list(summaries.directory.glob("*.replay"))
    assert await handoff.CheckpointHandoff(api_key(), generate).resolve(scope, checkpoint())


@pytest.mark.parametrize("restricted", ["model", "account"])
async def test_cached_handoff_rechecks_permissions(env, restricted):
    scope, origins, summaries, calls, generate = env
    await handoff.CheckpointHandoff(api_key(), generate).resolve(scope, checkpoint())
    key = (
        replace(api_key(), allowed_models=["anthropic/claude-opus-5-5"])
        if restricted == "model"
        else replace(api_key(), account_assignment_scope_enabled=True, assigned_account_ids=["other-owner"])
    )
    with pytest.raises(Exception) as error:
        await handoff.CheckpointHandoff(key, generate).resolve(scope, checkpoint())
    assert "access" in str(error.value).lower() or "scope" in json.dumps(getattr(error.value, "payload", {}))
    assert len(calls) == 1


@pytest.mark.parametrize("state", ["expired", "corrupt", "oversize"])
async def test_summary_cache_miss_regenerates_from_provenance(env, monkeypatch, state):
    scope, origins, summaries, calls, generate = env
    await handoff.CheckpointHandoff(api_key(), generate).resolve(scope, checkpoint())
    path = next(summaries.directory.glob("*.replay"))
    if state == "expired":
        stamp = path.stat().st_mtime - 3601
        os.utime(path, (stamp, stamp))
    elif state == "corrupt":
        path.write_bytes(b"bad digest\n{}")
    else:
        monkeypatch.setattr(
            handoff, "handoff_store", lambda: HTTPFallbackReplayStore(summaries.directory, max_entry_bytes=100)
        )
        with pytest.raises(ProxyResponseError):
            await handoff.CheckpointHandoff(api_key(), generate).resolve(scope, checkpoint())
        return
    assert await handoff.CheckpointHandoff(api_key(), generate).resolve(scope, checkpoint())
    assert len(calls) == 2


async def test_summary_survives_origin_expiry_and_still_checks_access(env):
    scope, origins, summaries, calls, generate = env
    resolver = handoff.CheckpointHandoff(api_key(), generate)
    first = await resolver.resolve(scope, checkpoint())
    path = next(origins.directory.glob("*.replay"))
    stamp = path.stat().st_mtime - 3601
    os.utime(path, (stamp, stamp))
    assert await origins.load(scope, handoff.checkpoint_digest("PRIVATE_NATIVE")) is None
    assert await resolver.resolve(scope, checkpoint()) == first
    restricted = replace(api_key(), account_assignment_scope_enabled=True, assigned_account_ids=["other-owner"])
    with pytest.raises(ProxyResponseError) as error:
        await handoff.CheckpointHandoff(restricted, generate).resolve(scope, checkpoint())
    assert error.value.status_code == 403 and len(calls) == 1


async def test_task_cancellation_releases_claim(env):
    scope, origins, summaries, calls, generate = env
    started = asyncio.Event()
    finished = asyncio.Event()

    async def blocked(origin, item):
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            finished.set()

    task = asyncio.create_task(handoff.CheckpointHandoff(api_key(), blocked).resolve(scope, checkpoint()))
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert finished.is_set()
    assert not list(summaries.directory.glob("*.replay"))
    assert await handoff.CheckpointHandoff(api_key(), generate).resolve(scope, checkpoint())


async def test_claim_storage_error_never_generates(env, monkeypatch):
    scope, origins, summaries, calls, generate = env

    def fail(*args, **kwargs):
        raise OSError("PRIVATE_STORAGE_DETAIL")

    monkeypatch.setattr(handoff.HandoffClaims, "_change", fail)
    with pytest.raises(ProxyResponseError) as error:
        await handoff.CheckpointHandoff(api_key(), generate).resolve(scope, checkpoint())
    assert error.value.status_code == 503 and "PRIVATE" not in json.dumps(error.value.payload)
    assert not calls


async def test_cancellation_during_claim_acquisition_releases_committed_claim(env, monkeypatch):
    scope, origins, summaries, calls, generate = env
    original = handoff.HandoffClaims._change
    acquired, finish = asyncio.Event(), threading.Event()
    loop = asyncio.get_running_loop()

    def slow_acquire(self, key, token, *, release):
        changed = original(self, key, token, release=release)
        if not release:
            loop.call_soon_threadsafe(acquired.set)
            assert finish.wait(5)
        return changed

    monkeypatch.setattr(handoff.HandoffClaims, "_change", slow_acquire)
    task = asyncio.create_task(handoff.CheckpointHandoff(api_key(), generate).resolve(scope, checkpoint()))
    await acquired.wait()
    task.cancel()
    finish.set()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert not calls
    assert await handoff.CheckpointHandoff(api_key(), generate).resolve(scope, checkpoint())


async def test_abandoned_claim_expires_and_old_release_cannot_remove_new_claim(tmp_path):
    clock = VirtualClock()
    claims = handoff.HandoffClaims(tmp_path, clock=clock)
    scope = ApiKeyScope("key")
    first = await claims.acquire(scope, "digest")
    assert first is not None and await claims.acquire(scope, "digest") is None
    clock.advance(handoff.HANDOFF_TIMEOUT_SECONDS + 31)
    second = await handoff.HandoffClaims(tmp_path, clock=clock).acquire(scope, "digest")
    assert second is not None and first != second
    await claims.release(first)
    assert await claims.acquire(scope, "digest") is None
    await claims.release(second)
    assert await claims.acquire(scope, "digest") is not None


@pytest.mark.parametrize("state", ["expired", "corrupt", "evicted", "oversize"])
async def test_unavailable_provenance_cannot_generate(env, monkeypatch, state):
    scope, origins, summaries, calls, generate = env
    path = next(origins.directory.glob("*.replay"))
    if state == "expired":
        stamp = path.stat().st_mtime - 3601
        os.utime(path, (stamp, stamp))
    elif state == "corrupt":
        path.write_bytes(b"invalid digest\n{}")
    elif state == "evicted":
        origins.max_entries = 0
        await origins.sweep()
    else:
        monkeypatch.setattr(
            handoff, "origin_store", lambda: HTTPFallbackReplayStore(origins.directory, max_entry_bytes=100)
        )
    assert await handoff.CheckpointHandoff(api_key(), generate).resolve(scope, checkpoint()) is None
    assert not calls


async def test_periodic_maintenance_sweeps_new_namespaces(env, monkeypatch, tmp_path):
    from app.modules.proxy._service.websocket import mixin

    scope, origins, summaries, calls, generate = env
    await handoff.CheckpointHandoff(api_key(), generate).resolve(scope, checkpoint())
    for store in (origins, summaries):
        path = next(store.directory.glob("*.replay"))
        stamp = path.stat().st_mtime - 3601
        os.utime(path, (stamp, stamp))
    monkeypatch.setattr(mixin, "origin_store", lambda: origins)
    monkeypatch.setattr(mixin, "handoff_store", lambda: summaries)
    legacy = HTTPFallbackReplayStore(tmp_path / "legacy")
    monkeypatch.setattr(mixin, "checkpoint_store", lambda: legacy)
    await mixin._WebSocketMixin.sweep_http_fallback_replay(SimpleNamespace(_http_fallback_replay_store=legacy))
    assert not list(origins.directory.glob("*.replay")) and not list(summaries.directory.glob("*.replay"))
